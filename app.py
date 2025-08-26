import os
import json
import base64
import datetime
import pandas as pd
import streamlit as st
import gspread

from email.mime.text import MIMEText

# Google Sheets (service account)
from google.oauth2.service_account import Credentials as SA_Credentials

# Gmail (user OAuth token JSON pasted in Secrets)
from google.oauth2.credentials import Credentials as User_Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ======================
# CONFIG
# ======================
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

CONTACT_HEADERS = [
    "Contact ID", "Name", "Email", "Phone", "Company", "Industry",
    "Status", "Assigned Contractor", "Created Date"
]
NOTES_HEADERS = ["Note ID", "Contact ID", "Contractor", "Date", "Note"]
EMAIL_HEADERS = ["Email ID", "Contact ID", "Subject", "Sent By", "Date", "Status"]

# ======================
# GOOGLE SHEETS AUTH (via Streamlit Secrets)
# ======================
def connect_to_sheets(sheet_name: str):
    try:
        info = dict(st.secrets["gcp_service_account"])
    except Exception:
        st.error("Missing [gcp_service_account] in Secrets.")
        st.stop()

    try:
        creds = SA_Credentials.from_service_account_info(info, scopes=SHEETS_SCOPES)
        client = gspread.authorize(creds)
    except Exception as e:
        st.error(f"Could not build Google Sheets credentials. Details: {e}")
        st.stop()

    try:
        return client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        st.error(
            f"Spreadsheet '{sheet_name}' not found. "
            f"Share it with the service account: {info.get('client_email','(unknown)')}."
        )
        st.stop()

# ======================
# GMAIL AUTH (token JSONs in Secrets)
# ======================
def gmail_service_from_secrets(account_key: str):
    """
    account_key: 'charles' or 'alexandria'
    Requires Secrets section:
      [gmail_tokens]
      charles = """{... oauth token json ...}"""
      alexandria = """{... oauth token json ...}"""
    The token JSON must contain refresh_token, client_id, client_secret, etc.
    """
    tokens = st.secrets.get("gmail_tokens", None)
    if not tokens or account_key not in tokens:
        return None, f"Missing gmail token JSON for '{account_key}' in [gmail_tokens] secrets."

    try:
        token_info = json.loads(tokens[account_key])
        creds = User_Credentials.from_authorized_user_info(token_info, GMAIL_SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        service = build("gmail", "v1", credentials=creds)
        return service, None
    except Exception as e:
        return None, f"Gmail credentials error for '{account_key}': {e}"

def send_email(service, to, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}
    sent = service.users().messages().send(userId="me", body=body).execute()
    return sent.get("id", "")

# ======================
# SHEET INIT
# ======================
def setup_sheets(sheet):
    try:
        sheet.worksheet("Contacts")
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Contacts", rows="100", cols="10")
        ws.append_row(CONTACT_HEADERS)

    try:
        sheet.worksheet("Notes")
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Notes", rows="100", cols="10")
        ws.append_row(NOTES_HEADERS)

    try:
        sheet.worksheet("Email_Log")
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Email_Log", rows="100", cols="10")
        ws.append_row(EMAIL_HEADERS)

# ======================
# CRM HELPERS
# ======================
def get_all_contacts(sheet):
    ws = sheet.worksheet("Contacts")
    return ws.get_all_records(expected_headers=CONTACT_HEADERS)

def add_contact(sheet, name, email, phone, company, industry, status, contractor):
    """Enforce uniqueness by Email; return existing ID if already present."""
    ws = sheet.worksheet("Contacts")
    today = datetime.date.today().isoformat()
    contacts = ws.get_all_records(expected_headers=CONTACT_HEADERS)

    if email:
        for r in contacts:
            if r["Email"] == email:
                return r["Contact ID"]  # already exists

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
st.set_page_config(page_title="Alexandria CRM", layout="wide")
st.title("📋 Alexandria CRM")

sheet = connect_to_sheets("Alexandria's CRM")
setup_sheets(sheet)

menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Pipeline View", "Add Contact", "Update Contact",
     "Send Email", "Notes", "Email Log", "Export"]
)

# Dashboard
if menu == "Dashboard":
    st.subheader("All Contacts")
    contacts = get_all_contacts(sheet)
    for c in contacts:
        c["Last Contacted"] = compute_last_contacted(sheet, c["Contact ID"])
    df = pd.DataFrame(contacts)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All"] + sorted(df["Status"].dropna().unique().tolist()))
    with col2:
        contractor_filter = st.selectbox("Filter by Contractor", ["All"] + sorted(df["Assigned Contractor"].dropna().unique().tolist()))
    with col3:
        industry_filter = st.selectbox("Filter by Industry", ["All"] + sorted(df["Industry"].dropna().unique().tolist()))
    with col4:
        search_filter = st.text_input("Search by Name/Email/Company")

    if status_filter != "All":
        df = df[df["Status"] == status_filter]
    if contractor_filter != "All":
        df = df[df["Assigned Contractor"] == contractor_filter]
    if industry_filter != "All":
        df = df[df["Industry"] == industry_filter]
    if search_filter:
        mask = (
            df["Name"].str.contains(search_filter, case=False, na=False) |
            df["Email"].str.contains(search_filter, case=False, na=False) |
            df["Company"].str.contains(search_filter, case=False, na=False)
        )
        df = df[mask]

    st.dataframe(df, use_container_width=True)

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
                st.markdown(f"**{row['Name']}** ({row['Company']}, {row['Industry']}) — {row['Assigned Contractor']}")

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
            st.error("❌ Name and Email are required.")
        else:
            cid = add_contact(sheet, name, email, phone, company, industry, status, contractor)
            st.success(f"✅ Contact {name} added/updated with ID {cid}")

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
                        contact_id, name, email, phone, company, industry, status, contractor, contact["Created Date"]
                    ]])
                    st.success(f"✅ Contact {name} (ID {contact_id}) updated")
                    break

# Send Email
elif menu == "Send Email":
    st.subheader("Send Email to Contact")
    contacts = get_all_contacts(sheet)
    if contacts:
        # Deduplicate by email to avoid repeats in dropdown
        unique_contacts = {c["Email"] or f"noemail-{c['Contact ID']}": c for c in contacts}.values()
        contact_names = [f"{c['Contact ID']} - {c['Name']}" for c in unique_contacts]

        choice = st.selectbox("Choose Contact", contact_names)
        contact_id = choice.split(" - ")[0]
        contact = next(c for c in contacts if str(c["Contact ID"]) == contact_id)

        subject = st.text_input("Subject")
        message_text = st.text_area("Message")
        account_choice = st.selectbox("Send From", ["Charles", "Alexandria"])

        if st.button("Send Email"):
            if not contact["Email"]:
                st.error("❌ This contact has no email address.")
            else:
                key = "charles" if account_choice == "Charles" else "alexandria"
                gmail_service, err = gmail_service_from_secrets(key)
                if err:
                    st.error(
                        f"{err}\n\n"
                        "Generate the token locally (one time) and paste it into Secrets under [gmail_tokens]."
                    )
                else:
                    email_id = send_email(gmail_service, contact["Email"], subject, message_text)
                    log_email(sheet, email_id, contact_id, subject, account_choice, "Sent")
                    st.success(f"📧 Sent from {account_choice} to {contact['Name']} ({contact['Email']})")

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
    st.table(notes if notes else [])

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


