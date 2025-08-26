📋 Alexandria CRM

A lightweight, cloud-based CRM system built with Python, Streamlit, Google Sheets, and Gmail API.
This CRM helps small teams manage contacts, track notes, send emails, and visualize pipelines — all while staying lean and easy to extend.

🚀 Features

Contact Management

Store name, email, phone, company, industry, status, contractor, and created date.

Update existing contacts with ease.

Notes Tracking

Add and view notes per contact.

Keep follow-up records tied to each lead.

Email Integration (Gmail API)

Send emails directly from the CRM.

Choose between multiple Gmail accounts (e.g., Charles & Alexandria).

Automatically log sent emails into Google Sheets.

Pipeline View

Visualize contacts by status: New Lead, In Progress, Closed.

Quickly scan who is where in your pipeline.

Dashboard Filters

Filter contacts by status, contractor, or industry.

Search by name, email, or company.

Export to CSV

Export contacts for backup or use in other tools.

🛠️ Tech Stack

Python 3.11+

Streamlit
 for the web UI

Google Sheets API
 for storage

Gmail API
 for email sending

Pandas
 for data handling

📂 Project Structure
AlexandriaCRM/
│
├── app.py                  # Main Streamlit app
├── requirements.txt        # Dependencies
├── README.md               # Project documentation
├── .gitignore              # Ignore JSON secrets/tokens
└── .streamlit/
    └── secrets.toml        # Streamlit Cloud secrets (not pushed to GitHub)

⚙️ Setup
1. Clone Repo
git clone https://github.com/charlesmartinedd/alexandria-crm.git
cd alexandria-crm

2. Install Requirements
pip install -r requirements.txt

3. Configure Google APIs

Enable Google Sheets API and Gmail API in Google Cloud.

Download your Service Account JSON (for Sheets).

Download your OAuth Client Secret JSON (for Gmail).

Add them as Streamlit secrets (see below).

4. Run Locally
streamlit run app.py

🔑 Secrets Setup

Use .streamlit/secrets.toml (or Streamlit Cloud → Secrets tab):

[gcp_service_account]
type = "service_account"
project_id = "alexandriacrm"
private_key_id = "XXXX"
private_key = "-----BEGIN PRIVATE KEY-----\nXXXX\n-----END PRIVATE KEY-----\n"
client_email = "alexandriacrm@alexandriacrm.iam.gserviceaccount.com"
client_id = "XXXX"
token_uri = "https://oauth2.googleapis.com/token"

[gmail]
client_id = "764698466961-xxxxx.apps.googleusercontent.com"
client_secret = "XXXXX"
redirect_uris = ["http://localhost"]

🌐 Deploy on Streamlit Cloud

Push repo to GitHub.

Go to share.streamlit.io
.

Link your repo.

Add requirements.txt and secrets.

Launch 🚀

📸 Screenshots
Dashboard View

(screenshot placeholder)

Pipeline View

(screenshot placeholder)

👤 Author

Charles Martin (Carlitos)
📧 charlesmartinedd@gmail.com

🚀 Alexandria’s Design

📜 License

MIT License — free to use, modify, and distribute.