import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# -----------------------------
# Google Sheets Connection
# -----------------------------
def connect_to_sheets(sheet_name):
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    return client.open(sheet_name)

# -----------------------------
# Sheet Setup
# -----------------------------
CONTACT_HEADERS = ["Contact ID", "Name", "Email", "Phone", "Company", "Industry",
                   "Status", "Assigned Contractor", "Created Date"]
NOTES_HEADERS = ["Note ID", "Contact ID", "Contractor", "Date", "Note"]
EMAIL_HEADERS = ["Email ID", "Contact ID", "Subject", "Sent By", "Date", "Status"]

def setup_sheets(sheet):
    try:
        contacts_ws = sheet.worksheet("Contacts")
    except gspread.exceptions.WorksheetNotFound:
        contacts_ws = sheet.add_worksheet(title="Contacts", rows="100", cols="10")
        contacts_ws.append_row(CONTACT_HEADERS)

    try:
        notes_ws = sheet.worksheet("Notes")
    except gspread.exceptions.WorksheetNotFound:
        notes_ws = sheet.add_worksheet(title="Notes", rows="100", cols="10")
        notes_ws.append_row(NOTES_HEADERS)

    try:
        email_ws = sheet.worksheet("Email_Log")
    except gspread.exceptions.WorksheetNotFound:
        email_ws = sheet.add_worksheet(title="Email_Log", rows="100", cols="10")
        email_ws.append_row(EMAIL_HEADERS)

# -----------------------------
# CRUD Helpers
# -----------------------------
def get_all_contacts(sheet):
    ws = sheet.worksheet("Contacts")
    return ws.get_all_records(expected_headers=CONTACT_HEADERS)

def add_contact(sheet, name, email, phone, company, industry, status, contractor):
    ws = sheet.worksheet("Contacts")
    records = ws.get_all_records(expected_headers=CONTACT_HEADERS)
    new_id = len(records) + 1
    created_date = datetime.now().strftime("%Y-%m-%d")
    ws.append_row([new_id, name, email, phone, company, industry, status, contractor, created_date])
    return new_id

def add_note(sheet, contact_id, contractor, note):
    ws = sheet.worksheet("Notes")
    records = ws.get_all_records(expected_headers=NOTES_HEADERS)
    new_id = len(records) + 1
    date = datetime.now().strftime("%Y-%m-%d")
    ws.append_row([new_id, contact_id, contractor, date, note])
    return new_id

def log_email(sheet, contact_id, subject, sent_by, status="Sent"):
    ws = sheet.worksheet("Email_Log")
    records = ws.get_all_records(expected_headers=EMAIL_HEADERS)
    new_id = len(records) + 1
    date = datetime.now().strftime("%Y-%m-%d")
    ws.append_row([new_id, contact_id, subject, sent_by, date, status])
    return new_id

# -----------------------------
# Gmail (stub for now)
# -----------------------------
def send_email_stub(to_email, subject, body):
    # For now just simulate sending
    return f"Simulated send to {to_email} with subject '{subject}'"

# -----------------------------
# Streamlit UI
# -----------------------------
def main():
    st.set_page_config(page_title="Alexandria CRM", layout="wide")
    st.title("📋 Alexandria CRM")

    sheet = connect_to_sheets("Alexandria's CRM")
    setup_sheets(sheet)

    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Contact", "Add Note", "Send Email"])

    if menu == "Dashboard":
        st.subheader("All Contacts")
        contacts = get_all_contacts(sheet)
        st.dataframe(contacts)

    elif menu == "Add Contact":
        st.subheader("Add New Contact")
        with st.form("contact_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            company = st.text_input("Company")
            industry = st.text_input("Industry")
            status = st.selectbox("Status", ["New Lead", "Contacted", "In Progress", "Closed"])
            contractor = st.text_input("Assigned Contractor")
            submitted = st.form_submit_button("Add Contact")
            if submitted:
                if not name:
                    st.error("Name is required.")
                else:
                    cid = add_contact(sheet, name, email, phone, company, industry, status, contractor)
                    st.success(f"✅ Contact {name} added with ID {cid}")

    elif menu == "Add Note":
        st.subheader("Add Note to Contact")
        contacts = get_all_contacts(sheet)
        if contacts:
            contact_options = [f"{c['Contact ID']} - {c['Name']}" for c in contacts]
            choice = st.selectbox("Choose Contact", contact_options)
            contact_id = int(choice.split(" - ")[0])
            contractor = st.text_input("Contractor")
            note = st.text_area("Note")
            if st.button("Add Note"):
                nid = add_note(sheet, contact_id, contractor, note)
                st.success(f"📝 Note added with ID {nid}")
        else:
            st.warning("No contacts available. Please add a contact first.")

    elif menu == "Send Email":
        st.subheader("Send Email to Contact")
        contacts = get_all_contacts(sheet)
        if contacts:
            contact_options = [f"{c['Contact ID']} - {c['Name']}" for c in contacts]
            choice = st.selectbox("Choose Contact", contact_options)
            contact_id = int(choice.split(" - ")[0])
            contact = next(c for c in contacts if c["Contact ID"] == contact_id)
            subject = st.text_input("Subject")
            message_text = st.text_area("Message")
            if st.button("Send Email"):
                if not contact["Email"]:
                    st.error("❌ This contact has no email saved. Add one before sending.")
                else:
                    msg_id = log_email(sheet, contact_id, subject, "System User")
                    result = send_email_stub(contact["Email"], subject, message_text)
                    st.success(f"📧 Email logged (ID {msg_id}): {result}")
        else:
            st.warning("No contacts available. Please add a contact first.")

if __name__ == "__main__":
    main()
