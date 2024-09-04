import streamlit as st
from PIL import Image
import pandas as pd
import requests  # To fetch files from GitHub
from io import BytesIO
import openai
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from passport_verify import passport_verify
from license_verify import license_verify
from income_verify import checkbankstatement, checkpayslip

# Define GitHub raw URLs
EXCEL_FILE_URL = "https://raw.githubusercontent.com/AnuragAnand14/final/main/ticket_updates.xlsx"  # Replace with your actual GitHub raw URL

# Retrieve API key from Streamlit secrets
openai_api_key = st.secrets["api"]["key"]

# Initialize OpenAI with the API key
openai.api_key = openai_api_key

def get_dropdown_names(TicketType):
    if TicketType == "Income":
        return ["Payslip", "Bank Statement"]
    elif TicketType == "Fraud":
        return ["Passport", "Driving License"]
    elif TicketType == "Both":
        return ["Payslip", "Bank Statement", "Passport", "Driving License"]

def get_ticket_type(ticket_id, excel_file_url):
    # Fetch the Excel file from GitHub
    response = requests.get(excel_file_url)
    if response.status_code == 200:
        df = pd.read_excel(BytesIO(response.content))

        # Check if the Ticket ID exists in the DataFrame
        if ticket_id in df['Ticket No'].values:
            # Retrieve the Ticket Type based on the Ticket ID
            ticket_type = df.loc[df['Ticket No'] == ticket_id, 'Ticket Type'].values[0]
            return ticket_type
        else:
            return "Ticket ID not found."
    else:
        return "Failed to fetch the Excel file."

def get_uuid(ticket_id, excel_file_url):
    # Fetch the Excel file from GitHub
    response = requests.get(excel_file_url)
    if response.status_code == 200:
        df = pd.read_excel(BytesIO(response.content))

        # Check if the Ticket ID exists in the DataFrame
        if ticket_id in df['Ticket No'].values:
            uuid = df.loc[df['Ticket No'] == ticket_id, 'UUID'].values[0]
            return uuid
        else:
            return "UUID not found."
    else:
        return "Failed to fetch the Excel file."

def save_uploaded_file(uploaded_file, folder_path, save_name):
    # Save the file in the local directory for verification
    if uploaded_file is not None and save_name:
        original_filename = uploaded_file.name
        _, file_extension = os.path.splitext(original_filename)
        if not os.path.splitext(save_name)[1]:
            save_name += file_extension
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, save_name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def verify_document(document_type, file_path, first_name, last_name):
    if document_type == "Passport":
        result = passport_verify(file_path, first_name, last_name)
    elif document_type == "Driving License":
        result = license_verify(file_path, first_name, last_name)
    elif document_type == "Payslip":
        result = checkpayslip(file_path)
    elif document_type == "Bank Statement":
        result = checkbankstatement(file_path)
    else:
        result = "Invalid document type."
    return result

def main():
    st.title("Document Upload Portal")

    # Initialize session state to track the uploaded file
    if 'last_uploaded_file' not in st.session_state:
        st.session_state.last_uploaded_file = None

    ticket_id = st.text_input("Enter your Ticket ID:")
    ticket_type = get_ticket_type(ticket_id, EXCEL_FILE_URL)

    if ticket_type != "Ticket ID not found.":
        document_type = st.selectbox("Select document type", get_dropdown_names(ticket_type))

        # Allow the user to upload the document
        uploaded_doc = st.file_uploader("Upload your document", type=["pdf", "png", "jpg", "jpeg"])

        # Only save the file if a new file has been uploaded
        if uploaded_doc is not None and uploaded_doc != st.session_state.last_uploaded_file:
            uuid = get_uuid(ticket_id, EXCEL_FILE_URL)
            if "UUID not found." not in uuid:
                file_path = save_uploaded_file(uploaded_doc, document_type, uuid)
                st.session_state.last_uploaded_file = uploaded_doc
                st.success(f"File saved successfully at {file_path}")

                verification_result = verify_document(document_type, file_path, "angela", "zoe")

                # Show different prompts based on the result of passport_verify()
                if verification_result == -1:
                    st.error("Please upload the correct document.")
                elif verification_result == 0:
                    st.warning("Please reupload")
                elif verification_result == 1:
                    st.success(f"{document_type} Verification successful.")
                else:
                    st.info("Unexpected result from passport verification.")
            else:
                st.error("Failed to fetch UUID from Excel file.")
        else:
            st.info("No new file uploaded, or file already saved.")
    else:
        st.error("Ticket ID not found in the provided data.")

if __name__ == "__main__":
    main()
