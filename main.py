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
        model = request.form.get('model', 'gpt-4o-mini')  # Default to gpt-4o-mini if not specified
        if f:
            filename = secure_filename(f.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(file_path)
            return process_pdf(file_path, model)
    return render_template('index.html')


def process_pdf(file_path, model):
    # Extract text from PDF
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

    # Generate all summaries using the new function with the specified model
    summaries = generate_summaries(text, model)

    # Clean up: delete the uploaded file
    os.remove(file_path)

    return jsonify(summaries)


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

    return {key: format_summary(value) for key, value in summaries.items()}


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