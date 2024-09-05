# Flask backend (app.py)
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from flask_dropzone import Dropzone
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import PyPDF2
from openai import OpenAI
import yaml
from markupsafe import escape, Markup
import markdown
import sqlite3
import json
import uuid
from collections import OrderedDict
import hashlib
from datetime import datetime

def adapt_datetime(ts):
    return ts.isoformat()

sqlite3.register_adapter(datetime, adapt_datetime)

class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)

# Define paper_storage at the module level
paper_storage = LimitedSizeDict(size_limit=100)  # Adjust size_limit as needed

def load_config(app, config_file='settings.yaml'):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    app.config.update(config)

app = Flask(__name__)
app.secret_key = app.config.get('SECRET_KEY', 'fallback_secret_key')
load_config(app)
dropzone = Dropzone(app)

client = OpenAI(api_key=app.config['OPENAI_API_KEY'])

# Set up LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin):
    def __init__(self, id, username, password, is_admin):
        self.id = id
        self.username = username
        self.password = password
        self.is_admin = is_admin

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  is_admin BOOLEAN NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS papers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  hash TEXT UNIQUE NOT NULL,
                  filename TEXT NOT NULL,
                  full_text TEXT NOT NULL,
                  short_summary TEXT NOT NULL,
                  extended_summary TEXT NOT NULL,
                  methods_discussion TEXT NOT NULL,
                  theory_discussion TEXT NOT NULL,
                  created_at DATETIME NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  paper_id INTEGER NOT NULL,
                  user_message TEXT NOT NULL,
                  ai_response TEXT NOT NULL,
                  created_at DATETIME NOT NULL,
                  FOREIGN KEY (paper_id) REFERENCES papers (id))''')
    conn.commit()
    conn.close()

init_db()

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2], user[3])
    return None

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            login_user(User(user[0], user[1], user[2], user[3]))
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Admin page
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form['action']
        if action == 'add':
            username = request.form['username']
            password = request.form['password']
            is_admin = 'is_admin' in request.form
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                          (username, generate_password_hash(password), is_admin))
                conn.commit()
                flash('User added successfully')
            except sqlite3.IntegrityError:
                flash('Username already exists')
            conn.close()
        elif action == 'delete':
            user_id = request.form['user_id']
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            flash('User deleted successfully')
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username, is_admin FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        f = request.files.get('file')
        model = request.form.get('model', 'gpt-4o-mini')
        if f:
            filename = secure_filename(f.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(file_path)
            
            try:
                # Generate file hash
                with open(file_path, 'rb') as file:
                    file_hash = hashlib.md5(file.read()).hexdigest()
                
                # Check if paper already exists
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("SELECT * FROM papers WHERE hash = ?", (file_hash,))
                existing_paper = c.fetchone()
                
                if existing_paper:
                    return redirect(url_for('paper', file_hash=file_hash))
                
                full_text, summaries = process_pdf(file_path, model)
                
                # Store paper in database
                c.execute('''INSERT INTO papers (hash, filename, full_text, short_summary, extended_summary, methods_discussion, theory_discussion, created_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (file_hash, filename, full_text, summaries['short_summary'], summaries['extended_summary'],
                           summaries['methods_discussion'], summaries['theory_discussion'], datetime.now()))
                conn.commit()
                conn.close()
                
                return redirect(url_for('paper', file_hash=file_hash))
            finally:
                # Ensure the file is removed even if an error occurs
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    return render_template('index.html')

@app.route('/paper/<file_hash>')
@login_required
def paper(file_hash):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM papers WHERE hash = ?", (file_hash,))
    paper = c.fetchone()
    
    if not paper:
        flash('Paper not found')
        return redirect(url_for('index'))
    
    # Format summaries as HTML
    formatted_paper = list(paper)
    for i in range(4, 8):  # Indices 4-7 contain the summaries
        formatted_paper[i] = format_summary(paper[i])
    
    c.execute("SELECT user_message, ai_response FROM chats WHERE paper_id = ? ORDER BY created_at", (paper[0],))
    chats = c.fetchall()
    conn.close()
    
    return render_template('paper.html', paper=formatted_paper, chats=chats, file_hash=file_hash)

@app.route('/chat/<file_hash>', methods=['POST'])
@login_required
def chat(file_hash):
    data = request.json
    user_message = data['message']
    model = data['model']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, full_text FROM papers WHERE hash = ?", (file_hash,))
    paper = c.fetchone()
    
    if not paper:
        return jsonify({"response": "Paper not found"})

    paper_id, full_text = paper

    conversation = [
        {"role": "system", "content": "You are an AI assistant specialized in discussing academic papers. Use the provided full text of the paper to answer questions from the user."},
        {"role": "user", "content": f"Here's the full text of the paper:\n\n{full_text}\n\nNow, please answer the following question: {user_message}"}
    ]

    response = client.chat.completions.create(
        model=model,
        messages=conversation
    )

    ai_message = response.choices[0].message.content.strip()

    c.execute('''INSERT INTO chats (paper_id, user_message, ai_response, created_at)
                 VALUES (?, ?, ?, ?)''', (paper_id, user_message, ai_message, datetime.now()))
    conn.commit()
    conn.close()

    return jsonify({"response": ai_message})

def process_pdf(file_path, model):
    # Extract text from PDF
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

    # Generate all summaries using the new function with the specified model
    summaries = generate_summaries(full_text, model)

    return full_text, summaries


def generate_summaries(text, model):
    messages = [
        {"role": "system", "content": "You are an AI assistant specialized in succinct summaries of academic papers. Your task is to provide a series of summaries and discussions about a paper, building upon previous information without redundancy."},
        {"role": "user", "content": "I will provide you with an academic paper. Please read it carefully and await further instructions for specific summaries and discussions."},
        {"role": "user", "content": text},
        {"role": "assistant", "content": "I have carefully read the academic paper and am ready for your specific requests."}
    ]

    def get_summary(prompt):
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        content = response.choices[0].message.content.strip()
        messages.append({"role": "assistant", "content": content})
        return content
    
    summaries = {}

    # Short summary
    summaries['short_summary'] = get_summary("Provide a 2-sentence summary of the paper.")

    # Extended summary
    summaries['extended_summary'] = get_summary("Now, provide a 250 word extended summary of the paper. Build upon the short summary you just provided, adding more details and key points. Avoid repeating information you've already mentioned.")

    # Methods discussion
    summaries['methods_discussion'] = get_summary("Next, provide a 150 word summary of the methods and data used in this paper. Focus on aspects not already covered in the summaries. If you've already mentioned some methods, you can briefly refer to them but provide more depth or new information.")

    # Theory discussion
    summaries['theory_discussion'] = get_summary("Finally, provide a 200 word discussion of the theoretical framework and contribution of this paper. Highlight aspects not already covered in previous summaries and discussions. If you've touched on theoretical points before, expand on them without repeating the same information.")

    return summaries  # Return the summaries without HTML formatting


def format_summary(summary):
    # Convert markdown to HTML
    html = markdown.markdown(summary)
    
    # Remove any potential extra newlines between tags
    html = html.replace('>\n<', '><')
    
    # Wrap the entire summary in a div tag
    return Markup(f'<div class="summary-content">{html}</div>')


if __name__ == '__main__':
    #app.run(debug=True)
    app.run(host='0.0.0.0', port=80)