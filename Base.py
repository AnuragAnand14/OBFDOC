import streamlit as st
import pandas as pd
import uuid
import pytesseract
from PIL import Image
import PyPDF2
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

# Function to send email using Gmail API
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

# Function to extract text from image or PDF
def extract_text(file):
    if file.type == "application/pdf":
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    else:
        image = Image.open(file)
        text = pytesseract.image_to_string(image)
    return text

# Function to verify document
def verify_document(text, customer_data):
    required_fields = ["Passport Country", "Expiry Date", "Passport Number", "F. Name", "L. Name"]
    for field in required_fields:
        if field.lower() not in text.lower():
            return "Oops! This seems to be the wrong document. Please try again."
    
    if len(text) < 50:  # Arbitrary threshold, adjust as needed
        return "Sorry, please upload a better image for processing."
    
    return "Thank you for providing the document. We will update you shortly!"

# Streamlit app
def main():
    st.title("Document Verification System")

    # Portal selection
    portal = st.sidebar.selectbox("Choose Portal", ["Admin", "Customer"])

    if portal == "Admin":
        st.header("Admin Section")
        uploaded_file = st.file_uploader("Upload customer data (CSV)", type="csv")
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write(df)
            
            if st.button("Send Trigger Emails"):
                base_upload_url = "http://localhost:8501"  # Replace with your actual upload portal URL
                
                for _, row in df.iterrows():
                    unique_id = str(uuid.uuid4())
                    unique_link = f"{base_upload_url}?id={unique_id}"
                    email_body = f"Hi {row['F.Name']} {row['L.Name']},\n\nWe have reviewed your application for {row['Product type']}  and request you to upload {row['Documents requested']} document to proceed further.\n\nPlease use this link to upload: {unique_link}\n\nThank you"
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

    elif portal == "Customer":
        st.header("Customer Document Upload")
        upload_link = st.text_input("Enter your unique upload link")
        if st.button("Go to Upload Portal") and upload_link:
            st.markdown(f"[Click here to upload your document]({upload_link})", unsafe_allow_html=True)
        
        uploaded_doc = st.file_uploader("Upload your document", type=["pdf", "png", "jpg", "jpeg"])
        
        if uploaded_doc is not None and upload_link:
            # Extract text from the document
            extracted_text = extract_text(uploaded_doc)
            
            # Verify the document
            result = verify_document(extracted_text, {})  # Pass customer data here
            
            st.write(result)
            
            # Update ticket status
            if 'tickets' in st.session_state:
                for ticket in st.session_state.tickets:
                    if ticket["link"] == upload_link:
                        ticket["status"] = "Document Uploaded"
                        
                        st.success("Document uploaded successfully!")

if __name__ == "__main__":
    main()
