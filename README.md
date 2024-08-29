# article_summaries

Flask app that uses the OpenAI API to generate quick summaries of academic articles using GPT without manually prompting ChatGPT repeatedly. By default, this app uses the GPT-4o-mini LLM, which is very cheap to use (probably less than $0.01 per summary).

To see how the app works, check out our demo video:

[![Demo Video](https://i3.ytimg.com/vi/RNvlYjW_OLw/hqdefault.jpg)](https://youtu.be/RNvlYjW_OLw)

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/your-repo-name.git
   cd your-repo-name
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up the settings.yaml file:
   - Create a file named `settings.yaml` in the root directory of the project.
   - Add the following content to the file:
     ```yaml
     # Upload configuration
     UPLOAD_FOLDER: 'uploads'

     # OpenAI configuration
     OPENAI_API_KEY: # Your OpenAI API key goes here, e.g. 'sk-proj-uidazio...'
     ```
   - Replace the placeholder text with your actual OpenAI API key, which you can find [here](https://platform.openai.com/api-keys).  Once you account is set up you can add credit [here](https://platform.openai.com/settings/organization/billing/overview). 

5. Run the app:
   ```
   python app.py
   ```

The app should now be running on `http://localhost`.

## Usage

Load `http://localhost` in a browser and then drag and drop a file into the Dropzone to get started.