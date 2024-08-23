# Flask backend (app.py)
from flask import Flask, jsonify, render_template, request
from flask_dropzone import Dropzone
import os
from werkzeug.utils import secure_filename
import PyPDF2
from openai import OpenAI
import yaml
from markupsafe import escape, Markup
import markdown

def load_config(app, config_file='settings.yaml'):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    app.config.update(config)

app = Flask(__name__)
load_config(app)
dropzone = Dropzone(app)

client = OpenAI(api_key=app.config['OPENAI_API_KEY'])

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Set up OpenAI API (replace with your actual API key)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        f = request.files.get('file')
        if f:
            filename = secure_filename(f.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(file_path)
            return process_pdf(file_path)
    return render_template('index.html')


def process_pdf(file_path):
    # Extract text from PDF
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

    # Generate summaries using GPT-4
    extended_summary = generate_summary(text, "extended")
    short_summary = generate_summary(text, "short")

    # Clean up: delete the uploaded file
    os.remove(file_path)

    # Format summaries for HTML display
    extended_summary = format_summary(extended_summary)
    short_summary = format_summary(short_summary)

    return jsonify({
        'extended_summary': extended_summary,
        'short_summary': short_summary
    })

def generate_summary(text, summary_type):
    prompt = f"Summarize the following academic paper. "
    if summary_type == "extended":
        prompt += "Provide an extended summary:"
    else:
        prompt += "Provide a 2-sentence summary:"

    response = client.chat.completions.create(model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that summarizes academic papers."},
        {"role": "user", "content": prompt + "\n\n" + text}
    ])
    return response.choices[0].message.content.strip()


def format_summary(summary):
    # Convert markdown to HTML
    html = markdown.markdown(summary)
    
    # Remove any potential extra newlines between tags
    html = html.replace('>\n<', '><')
    
    # Wrap the entire summary in a div tag
    return Markup(f'<div class="summary-content">{html}</div>')


if __name__ == '__main__':
    app.run(debug=True)