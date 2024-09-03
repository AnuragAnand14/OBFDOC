import streamlit as st
import pandas as pd
import uuid
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import base64
from email.mime.text import MIMEText

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    if st.session_state.get('token'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        st.session_state['token'] = creds.to_json()
    return build('gmail', 'v1', credentials=creds)

def send_email(to_email, subject, body):
    service = get_gmail_service()
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def main():
    st.title("Document Verification System - Admin Portal")

    uploaded_file = st.file_uploader("Upload customer data (CSV)", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write(df)
        
        if st.button("Send Trigger Emails"):
            base_upload_url = "https://docsupload.streamlit.app"  # Replace with your actual customer portal URL
            
            for _, row in df.iterrows():
                unique_id = str(uuid.uuid4())
                unique_link = f"{base_upload_url}?id={unique_id}"
                email_body = f"Hi {row['F.Name']} {row['L.Name']},\n\nWe have reviewed your application for {row['Product type']} and request you to upload {row['Documents requested']} document to proceed further.\n\nPlease use this link to upload: {unique_link}\n\nThank you"
                if send_email(row['Email'], "Document Upload Request", email_body):
                    if 'tickets' not in st.session_state:
                        st.session_state.tickets = []
                    st.session_state.tickets.append({
                        "customer": f"{row['F.Name']} {row['L.Name']}",
                        "product": row['Product type'],
                        "link": unique_link,
                        "status": "Pending"
                    })
            
            st.success("Trigger emails sent successfully!")

    # Display tickets
    if 'tickets' in st.session_state:
        st.header("Tickets")
        st.table(st.session_state.tickets)

if __name__ == "__main__":
    main()
