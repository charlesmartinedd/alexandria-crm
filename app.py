import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import os
import datetime
import pandas as pd

# ======================
# GOOGLE SHEETS AUTH
# ======================
def connect_to_sheets(json_keyfile, sheet_name):
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

# ======================
# GMAIL AUTH
# ======================
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def gmail_authenticate(client_secret_file, token_file="token_charles.json"):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def send_email(service, to, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}
    sent = service.users().messages().send(userId="me", body=body).execute()
    return sent["id"]

# ======================
# CRM HEADERS
# ======================
CONTACT_HEADERS = [
    "Contact ID", "Name", "Email", "Phone", "Company", "Industry",
    "Status", "Assigned Contractor", "Created Date"
]

NOTES_HEADERS = [
    "Note ID", "Contact ID", "Contractor", "Date", "Note"
]

EMAIL_HEADERS = [
    "Email ID", "Contact ID", "Subject", "Sent By", "Date", "Status"
]

# ======================
# CRM HELPERS
# ======================
def get_all_contacts(sheet):
    ws = sheet.worksheet("Contacts")
    return ws.get_all_records(expected_headers=CONTACT_HEADERS)

def add_contact(sheet, name, email, phone, company, industry, status, contractor):
    ws = sheet.worksheet("Contacts")
    today = datetime.date.today().isoformat()
    contacts = ws.get_all_records(expected_headers=CONTACT_HEADERS)
    contact_id = len(contacts) + 1

    row = {
        "Contact ID": contact_id,
        "Name": name,
        "Email": email,
        "Phone": phone,
        "Company": company,
        "Industry": industry,
        "Status": status,
        "Assigned Contractor": contractor,
        "Created Date": today
    }

    ws.append_row([row[h] for h in CONTACT_HEADERS])
    return contact_id

def log_email(sheet, email_id, contact_id, subject, sent_by, status="Sent"):
    ws = sheet.worksheet("Email_Log")
    today = datetime.date.today().isoformat()
    ws.append_row([email_id, contact_id, subject, sent_by, today, status])

def add_note(sheet, note_id, contact_id, contractor, note):
    ws = sheet.worksheet("Notes")
    today = datetime.date.today().isoformat()
    ws.append_row([note_id, contact_id, contractor, today, note])

def get_notes(sheet, contact_id):
    ws = sheet.worksheet("Notes")
    records = ws.get_all_records(expected_headers=NOTES_HEADERS)
    return [n for n in records if str(n["Contact ID"]) == str(contact_id)]

def get_emails(sheet, contact_id):
    ws = sheet.worksheet("Email_Log")
    records = ws.get_all_records(expected_headers=EMAIL_HEADERS)
    return [e for e in records if str(e["Contact ID"]) == str(contact_id)]

def compute_last_contacted(sheet, contact_id):
    notes = get_notes(sheet, contact_id)
    emails = get_emails(sheet, contact_id)
    dates = []
    if notes:
        dates.extend([datetime.date.fromisoformat(n["Date"]) for n in notes if n["Date"]])
    if emails:
        dates.extend([datetime.date.fromisoformat(e["Date"]) for e in emails if e["Date"]])
    return max(dates).isoformat() if dates else "—"

# ======================
# STREAMLIT UI
# ======================
st.title("📋 Alexandria CRM")

sheet = connect_to_sheets("alexandriacrm-f16eedb0450d.json", "Alexandria's CRM")

menu = st.sidebar.selectbox("Menu", [
    "Dashboard", "Pipeline View", "Add Contact", "Update Contact",
    "Send Email", "Notes", "Email Log", "Export"
])

# Dashboard
if menu == "Dashboard":
    st.subheader("All Contacts")
    contacts = get_all_contacts(sheet)
    for c in contacts:
        c["Last Contacted"] = compute_last_contacted(sheet, c["Contact ID"])
    df = pd.DataFrame(contacts)

    # ---- Filters ----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All"] + df["Status"].unique().tolist())
    with col2:
        contractor_filter = st.selectbox("Filter by Contractor", ["All"] + df["Assigned Contractor"].unique().tolist())
    with col3:
        industry_filter = st.selectbox("Filter by Industry", ["All"] + df["Industry"].unique().tolist())
    with col4:
        search_filter = st.text_input("Search by Name/Email/Company")

    if status_filter != "All":
        df = df[df["Status"] == status_filter]
    if contractor_filter != "All":
        df = df[df["Assigned Contractor"] == contractor_filter]
    if industry_filter != "All":
        df = df[df["Industry"] == industry_filter]
    if search_filter:
        df = df[df["Name"].str.contains(search_filter, case=False) |
                df["Email"].str.contains(search_filter, case=False) |
                df["Company"].str.contains(search_filter, case=False)]

    st.dataframe(df)

# Pipeline View
elif menu == "Pipeline View":
    st.subheader("Pipeline View")
    contacts = get_all_contacts(sheet)
    df = pd.DataFrame(contacts)

    stages = ["New Lead", "In Progress", "Closed"]
    cols = st.columns(len(stages))

    for i, stage in enumerate(stages):
        with cols[i]:
            st.markdown(f"### {stage}")
            stage_df = df[df["Status"] == stage]
            for _, row in stage_df.iterrows():
                st.markdown(f"**{row['Name']}** ({row['Company']}, {row['Industry']}) - {row['Assigned Contractor']}")

# Add Contact
elif menu == "Add Contact":
    st.subheader("Add New Contact")
    name = st.text_input("Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    company = st.text_input("Company")
    industry = st.text_input("Industry")
    status = st.selectbox("Status", ["New Lead", "In Progress", "Closed"])
    contractor = st.text_input("Assigned Contractor")

    if st.button("Add Contact"):
        if not name or not email:
            st.error("❌ Name and Email are required fields.")
        else:
            cid = add_contact(sheet, name, email, phone, company, industry, status, contractor)
            st.success(f"✅ Contact {name} added with ID {cid}")

# Update Contact
elif menu == "Update Contact":
    st.subheader("Update Existing Contact")
    contacts = get_all_contacts(sheet)
    if contacts:
        contact_names = [f"{c['Contact ID']} - {c['Name']}" for c in contacts]
        choice = st.selectbox("Choose Contact", contact_names)
        contact_id = choice.split(" - ")[0]
        contact = next(c for c in contacts if str(c["Contact ID"]) == contact_id)

        name = st.text_input("Name", value=contact["Name"])
        email = st.text_input("Email", value=contact["Email"])
        phone = st.text_input("Phone", value=contact["Phone"])
        company = st.text_input("Company", value=contact["Company"])
        industry = st.text_input("Industry", value=contact["Industry"])
        status = st.selectbox("Status", ["New Lead", "In Progress", "Closed"],
                              index=["New Lead", "In Progress", "Closed"].index(contact["Status"]))
        contractor = st.text_input("Assigned Contractor", value=contact["Assigned Contractor"])

        if st.button("Update Contact"):
            ws = sheet.worksheet("Contacts")
            all_records = ws.get_all_records(expected_headers=CONTACT_HEADERS)
            for idx, rec in enumerate(all_records, start=2):
                if str(rec["Contact ID"]) == str(contact_id):
                    ws.update(f"A{idx}:I{idx}", [[
                        contact_id,
                        name,
                        email,
                        phone,
                        company,
                        industry,
                        status,
                        contractor,
                        contact["Created Date"]
                    ]])
                    st.success(f"✅ Contact {name} (ID {contact_id}) updated successfully")
                    break

# Send Email
elif menu == "Send Email":
    st.subheader("Send Email to Contact")
    contacts = get_all_contacts(sheet)
    if contacts:
        contact_names = [f"{c['Contact ID']} - {c['Name']}" for c in contacts]
        choice = st.selectbox("Choose Contact", contact_names)
        contact_id = choice.split(" - ")[0]
        contact = next(c for c in contacts if str(c["Contact ID"]) == contact_id)

        subject = st.text_input("Subject")
        message_text = st.text_area("Message")

        # Choose sender account
        account_choice = st.selectbox("Send From", ["Charles", "Alexandria"])

        if st.button("Send Email"):
            if not contact["Email"]:
                st.error("❌ This contact does not have an email address saved.")
            else:
                if account_choice == "Charles":
                    gmail_service = gmail_authenticate(
                        "client_secret_764698466961-l3qantcn5e0ve9d7asif3gvm48brhlt7.apps.googleusercontent.com.json",
                        "token_charles.json"
                    )
                    sender = "Charles"
                else:
                    gmail_service = gmail_authenticate(
                        "client_secret_764698466961-l3qantcn5e0ve9d7asif3gvm48brhlt7.apps.googleusercontent.com.json",
                        "token_alexandria.json"
                    )
                    sender = "Alexandria"

                email_id = send_email(gmail_service, contact["Email"], subject, message_text)
                log_email(sheet, email_id, contact_id, subject, sender, "Sent")
                st.success(f"📧 Email sent from {sender} to {contact['Name']} ({contact['Email']})")

# Notes
elif menu == "Notes":
    st.subheader("Add/View Notes")
    contacts = get_all_contacts(sheet)
    contact_names = [f"{c['Contact ID']} - {c['Name']}" for c in contacts]
    choice = st.selectbox("Choose Contact", contact_names)
    contact_id = choice.split(" - ")[0]

    note = st.text_area("Note")
    contractor = st.text_input("Your Name")
    if st.button("Add Note"):
        note_id = len(sheet.worksheet("Notes").get_all_records(expected_headers=NOTES_HEADERS)) + 1
        add_note(sheet, note_id, contact_id, contractor, note)
        st.success("📝 Note added")

    st.subheader("History")
    notes = get_notes(sheet, contact_id)
    if notes:
        st.table(notes)
    else:
        st.info("No notes yet.")

# Email Log
elif menu == "Email Log":
    st.subheader("Email Log for All Contacts")
    ws = sheet.worksheet("Email_Log")
    emails = ws.get_all_records(expected_headers=EMAIL_HEADERS)
    st.table(emails)

# Export
elif menu == "Export":
    st.subheader("Export Contacts to CSV")
    contacts = get_all_contacts(sheet)
    df = pd.DataFrame(contacts)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Contacts CSV", data=csv, file_name="contacts.csv", mime="text/csv")
