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

## Adding the First User

Before you can use the application, you need to add the first user to the database. This user will have admin privileges. Follow these steps:

1. Ensure your application is set up and the database file (`users.db`) has been created.

2. Open a Python interactive shell in your project directory:
   ```
   python
   ```

3. In the Python shell, enter the following commands:
   ```python
   import sqlite3
   from werkzeug.security import generate_password_hash

   # Connect to the database
   conn = sqlite3.connect('users.db')
   c = conn.cursor()

   # Insert the first admin user
   username = 'admin'  # Change this to your desired admin username
   password = 'your_secure_password'  # Change this to a secure password
   hashed_password = generate_password_hash(password)
   is_admin = True

   c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
             (username, hashed_password, is_admin))

   # Commit the changes and close the connection
   conn.commit()
   conn.close()

   print("Admin user created successfully.")
   ```

4. Exit the Python shell:
   ```python
   exit()
   ```

Now you have created the first admin user. You can use these credentials to log in to the application and access the admin panel to manage other users.

## Security Note

Remember to change the default admin username and password to something secure. Never share your admin credentials or commit them to version control.

## Using the Application

1. Start the Flask application by running `python main.py`.
2. Open a web browser and navigate to `http://localhost:80` (or the appropriate address if you've configured it differently).
3. Log in using the admin credentials you created.
4. You can now use the application to summarize articles and manage users through the admin panel.