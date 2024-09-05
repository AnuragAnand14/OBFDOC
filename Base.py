import streamlit as st
import pandas as pd
import uuid
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import base64
from email.mime.text import MIMEText
import openpyxl
from twilio.rest import Client

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# File paths
CSV_FILE_PATH = "/Users/anurag.anand/BRAG/random_customer_data.csv"
EXCEL_FILE_PATH = "/Users/anurag.anand/BRAG/ticket_updates.xlsx"

# Twilio setup
account_sid = 'ACc5c1fc0f9f12f7d3f20c09f2002cfd05'
auth_token = '9dc5846028432bd394b4cb2ab08fa802'
twilio_client = Client(account_sid, auth_token)

# Set page config for wide layout
st.set_page_config(layout="wide")

# CSS styling
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .main {
        padding: 1rem;
    }
    h1, h2, h3, h4 {
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .stButton > button {
        width: 100%;
        padding: 0.5rem;
        font-size: 0.85rem;
        background-color: #3B82F6;
        color: white;
        font-weight: bold;
        border-radius: 5px;
    }
    .stButton > button:hover {
        background-color: #2563EB;
    }
    .customer-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .customer-info {
        margin-bottom: 0.5rem;
    }
    .ticket-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    .ticket-card {
        background-color: #f8fafc;
        padding: 0.75rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        flex: 1 1 calc(33.333% - 0.5rem);
        min-width: 200px;
    }
    .ticket-header {
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .ticket-info {
        margin-bottom: 0.25rem;
        font-size: 0.9rem;
    }
    .contact-buttons {
        display: flex;
        gap: 0.5rem;
    }
    .contact-buttons .stButton {
        flex: 1;
    }
    .stExpanderHeader {
        font-weight: bold;
        font-size: 1.1rem;
        color: #1E3A8A;
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 10px;
    }
    .stExpander {
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        margin-top: 20px;
    }
    .dataframe-container {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        overflow: hidden;
        margin-top: 10px;
    }
    .dataframe-table th {
        background-color: #1E3A8A !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 18px !important;
        padding: 10px !important;
        border-bottom: 1px solid #ddd !important;
    }
    .dataframe-table td {
        padding: 8px !important;
        font-size: 18px !important;
        color: #333 !important;
        border-bottom: 1px solid #ddd !important;
            
</style>
""", unsafe_allow_html=True)

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

def create_ticket(row, unique_link):
    ticket = {
        "UUID": str(uuid.uuid4()),
        "Ticket No": str(uuid.uuid4())[:8],
        "Ticket Type": row.get('Verification Type',''),
        "Customer F. Name": row.get('F.Name', ''),
        "Customer L. Name": row.get('L.Name', ''),
        "Loan Amount": row.get('Loan Amount', ''),
        "Loan Reference": row.get('Loan Reference', ''),
        "Product type": row.get('Product type', ''),
        "Documents requested": row.get('Documents requested', ''),
        "Document Link": unique_link,
        "Document Response": "",
        "Comment/Remark": "",
        "Status": "Pending"
    }
    update_excel_file(ticket)
    return ticket

def update_excel_file(ticket):
    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["UUID", "Ticket No", "Ticket Type", "Customer F. Name", "Customer L. Name", 
                                   "Loan Amount", "Loan Reference", "Product type", "Documents requested", 
                                   "Document Link", "Document Response", "Comment/Remark", "Status"])
    
    new_row = pd.DataFrame([{k: v for k, v in ticket.items() if v}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel(EXCEL_FILE_PATH, index=False)

def fetch_tickets_from_excel():
    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        return df.to_dict('records')
    except FileNotFoundError:
        st.error(f"Excel file not found: {EXCEL_FILE_PATH}")
        return []

def send_whatsapp_message(to_number, message):
    try:
        from_number = 'whatsapp:+14155238886'  # Your Twilio WhatsApp-enabled number
        message = twilio_client.messages.create(
            body=message,
            from_=from_number,
            to=f'whatsapp:{to_number}'
        )
        return True, f"WhatsApp message sent successfully. SID: {message.sid}"
    except Exception as e:
        return False, f"Error sending WhatsApp message: {e}"

def send_trigger_to_all(df):
    for index, row in df.iterrows():
        unique_id = str(uuid.uuid4())
        unique_link = f"https://docsupload.streamlit.app?id={unique_id}"
        message = f"""Hi {row.get('F.Name', '')} {row.get('L.Name','')},We have reviewed your application for {row.get('Product type', '')} and request you to upload {row.get('Documents requested', '')} document to proceed further.Please use the button below to upload:<a href="{unique_link}" style="display: inline-block; padding: 10px 20px; font-size: 16px; color: #ffffff; background-color: #007bff; text-align: center; text-decoration: none; border-radius: 5px;">Upload Document</a>Thank you"""
        
        if send_email(row.get('Email', ''), "Document Upload Request", message):
            st.session_state.tickets.append(create_ticket(row, unique_link))
            st.success(f"Email sent to {row.get('Email', '')}!")
        
        success, result = send_whatsapp_message(row.get('Phone', ''), message)
        if success:
            st.success(f"WhatsApp Reminder Sent to {row.get('F.Name', '')}!")
        else:
            st.error(result)

def main():
    # Add logo and title in a horizontal layout
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("/Users/anurag.anand/BRAG/download.jpeg", width=200)
    with col2:
        st.title("Customer Relationship Management")

    st.markdown("---")

    # Load data from the CSV file
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        st.success("Data loaded successfully")
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return

    # Fetch tickets from the Excel file
    tickets = fetch_tickets_from_excel()

    if 'tickets' not in st.session_state:
        st.session_state.tickets = []

    # Button to send trigger to all
    if st.button("Contact All Users"):
        send_trigger_to_all(df)

    # Display all customer details with individual trigger buttons
    st.subheader("Customer Details")
    for index, row in df.iterrows():
        with st.container():
            st.markdown('<div class="customer-card">', unsafe_allow_html=True)
            
            # Customer info and trigger buttons
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.markdown(f'<div class="customer-info"><strong>{row.get("F.Name", "")} {row.get("L.Name", "")}</strong></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="customer-info"><strong>Email:</strong> {row.get("Email", "")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="customer-info"><strong>Phone:</strong> {row.get("Phone", "")}</div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="customer-info"><strong>Product:</strong> {row.get("Product type", "")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="customer-info"><strong>Verification:</strong> {row.get("Verification Type", "")}</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="contact-buttons">', unsafe_allow_html=True)
                if st.button("Contact via Email", key=f"email_{index}"):
                    unique_id = str(uuid.uuid4())
                    unique_link = f"https://docsupload.streamlit.app?id={unique_id}"
                    email_body =f"""Hi {row.get('F.Name', '')} {row.get('L.Name','')},We have reviewed your application for {row.get('Product type', '')} and request you to upload {row.get('Documents requested', '')} document to proceed further.Please use the button below to upload:<a href="{unique_link}" style="display: inline-block; padding: 10px 20px; font-size: 16px; color: #ffffff; background-color: #007bff; text-align: center; text-decoration: none; border-radius: 5px;">Upload Document</a>Thank you"""
                    if send_email(row.get('Email', ''), "Document Upload Request", email_body):
                        st.session_state.tickets.append(create_ticket(row, unique_link))
                        st.success(f"Email sent to {row.get('Email', '')}!")
                
                if st.button("Contact via WhatsApp", key=f"whatsapp_{index}"):
                    unique_id = str(uuid.uuid4())
                    unique_link = f"https://docsupload.streamlit.app?id={unique_id}"
                    whatsapp_message = f"Hi {row.get('F.Name', '')} {row.get('L.Name', '')},\n\nWe have reviewed your application for {row.get('Product type', '')} and request you to upload {row.get('Documents requested', '')} document to proceed further.\n\nPlease use this link to upload: {unique_link}\n\nThank you"
                    success, result = send_whatsapp_message(row.get('Phone', ''), whatsapp_message)
                    if success:
                        st.session_state.tickets.append(create_ticket(row, unique_link))
                        st.success(f"WhatsApp message sent to {row.get('Phone', '')}!")
                    else:
                        st.error(result)
                st.markdown('</div>', unsafe_allow_html=True)

            # Display tickets related to the current customer
            customer_tickets = [ticket for ticket in tickets if ticket["Customer F. Name"] == row.get('F.Name', '') and ticket["Customer L. Name"] == row.get('L.Name', '')]
            if customer_tickets:
                st.markdown('<div class="ticket-container">', unsafe_allow_html=True)
                for ticket in customer_tickets:
                    st.markdown(f"""
                    <div class="ticket-card">
                        <div class="ticket-header">Ticket No: {ticket["Ticket No"]}</div>
                        <div class="ticket-info"><strong>Ticket Type:</strong> {ticket["Ticket Type"]}</div>
                        <div class="ticket-info"><strong>Documents Requested:</strong> {ticket["Documents requested"]}</div>
                        <div class="ticket-info"><strong>Status:</strong> {ticket["Status"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            # Display the Excel file in a collapsible format
    with st.expander("View Ticket Updates Excel File", expanded=False):
        st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
        try:
            df_excel = pd.read_excel(EXCEL_FILE_PATH)
            # Display the dataframe with Streamlit's default styling, but apply additional CSS
            st.dataframe(df_excel.style.set_properties(**{
                'background-color': '#f0f2f6',
                'color': '#333',
                'border-color': 'white'
            }).set_table_styles([
                {'selector': 'thead th', 'props': [('background-color', '#1E3A8A'), ('color', 'white'), ('font-weight', 'bold')]},
                {'selector': 'tbody td', 'props': [('padding', '10px'), ('border-bottom', '1px solid #ddd')]}
            ]))
        except FileNotFoundError:
            st.error(f"Excel file not found: {EXCEL_FILE_PATH}")
        except Exception as e:
            st.error(f"Error loading Excel file: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
if __name__ == "__main__":
    main()