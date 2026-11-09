
🛡️ CyberQuest AI – Interactive Cybersecurity Simulator
CyberQuest AI is an educational web application built with Python and Streamlit. It teaches cybersecurity through interactive, everyday safety scenarios rather than lessons alone.

Learners read a situation, choose an action, receive an explanation, and track their progress.

Features
Interactive missions: Practise recognizing phishing, password risks, unsafe public Wi-Fi, social engineering, update risks, and data-loss risks.
Difficulty filters: Choose Beginner, Intermediate, or Advanced.
AI scenario generator: Generate an additional safe learning scenario using the Groq API.
AI Cyber Teacher: Ask cybersecurity questions and receive explanations in simple English.
Score system: Earn XP for each completed mission.
Progress dashboard: Review completed missions, accuracy, points, and learning history.
Achievements: Unlock badges as you complete learning goals.
PDF certificate: Download an educational completion certificate after five missions.
SQLite storage: Save learner progress locally.
CSV export: Download your learning history.
Technology Stack
Python
Streamlit
Groq API
SQLite
Pandas
Plotly
ReportLab
Project Structure
CyberQuest-AI/
│
├── app.py
├── requirements.txt
└── README.md
The SQLite database (cyberquest.db) is created automatically when the app first runs. It is runtime data, not a source-code file.

Run Locally
1. Install Python
Install Python 3.10 or newer.

2. Download or clone the project
git clone https://github.com/YOUR-USERNAME/CyberQuest-AI.git
cd CyberQuest-AI
Or download the project ZIP and open its folder in your code editor.

3. Create a virtual environment (recommended)
Windows:

python -m venv venv
venv\Scripts\activate
macOS/Linux:

python3 -m venv venv
source venv/bin/activate
4. Install dependencies
pip install -r requirements.txt
5. Start the application
streamlit run app.py
Streamlit will show a local address in your terminal, usually http://localhost:8501.

Enable AI Features with Groq
The built-in missions, scoring, SQLite history, progress charts, achievements, and certificate work without an API key.

The AI Teacher and AI Scenario Generator require a Groq API key.

Create an account at Groq.
Create an API key in the Groq console.
Run the app.
Paste the key into the password field in the app's sidebar.
For local development, you can also use Streamlit secrets:

Create .streamlit/secrets.toml:

GROQ_API_KEY = "your_groq_api_key_here"
Do not upload your API key or secrets.toml to GitHub. Add secrets files to .gitignore.

Deploy on Streamlit Community Cloud
Push the three project files to a GitHub repository.
Sign in to Streamlit Community Cloud.
Create a new app and select your repository.
Set the main file path to app.py.
In the app's settings, open Secrets and add:
GROQ_API_KEY = "your_groq_api_key_here"
Deploy the application.
Important note about SQLite on cloud hosting
The app uses a local SQLite database file. On many hosted app environments, local files may not be permanent and can be reset when an app restarts or is redeployed. This version is suitable for a demo or learning project. For persistent multi-user progress, connect a hosted database in a future version.

Safety and Responsible Use
CyberQuest AI is designed for defensive cybersecurity awareness and education. It does not test real systems or perform security scans.

Only assess systems that you own or have explicit permission to test. Never share passwords, one-time codes, private keys, or API keys.

Future Improvements
User registration and secure authentication
Persistent hosted database
More scenario categories
Admin dashboard
More detailed learning paths
Improved certificate design
Multi-language explanations
Author
Developed as a Python and AI cybersecurity learning project.

