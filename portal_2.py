import streamlit as st
from PIL import Image
import PyPDF2
import os
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import openai
import fitz
import base64
from io import BytesIO
import io
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from passport_verify import passport_verify
from license_verify import license_verify
from income_verify import checkbankstatement, checkpayslip
import uuid
import pandas as pd
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse, parse_qs

# Adjust PATH for Homebrew
os.environ['PATH'] += os.pathsep + '/opt/homebrew/bin'

# Streamlit page configuration
st.set_page_config(page_title="OBF Document Validator", layout="wide")

# Database connection
try:
    connection = psycopg2.connect(
        host='bci-rd.postgres.database.azure.com',
        database='postgres',
        user='pgadmin',
        password='5y62<Rluh'
    )
    cursor = connection.cursor()
except psycopg2.Error as e:
    st.error(f"Failed to connect to the database: {e}")
    st.stop()

def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load CSS
load_css('styles2.css')

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def get_dropdown_names(TicketType):
    """Get document types based on ticket type."""
    options = {
        "Income": ["Payslip", "Bank Statement"],
        "Fraud": ["Passport", "Driving License"],
        "Both": ["Payslip", "Bank Statement", "Passport", "Driving License"]
    }
    return options.get(TicketType, [])

def get_ticket_type(ticket_id):
    """Retrieve ticket type from database."""
    if not ticket_id or not is_valid_uuid(ticket_id):
        return None
    
    query = sql.SQL("SELECT ticket_type FROM obf_tickets WHERE id = %s")
    try:
        cursor.execute(query, (ticket_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        st.error(f"Database error: {e}")
        return None

def get_document_details(ticket_id):
    """Fetch document links and verification responses."""
    query = """
    SELECT document_link, verification_response
    FROM obf_documents
    WHERE ticket_id = %s
    """
    try:
        cursor.execute(query, (ticket_id,))
        result = cursor.fetchall()
        return [row[0] for row in result], [row[1] for row in result]
    except psycopg2.Error as e:
        st.error(f"Database error: {e}")
        return [], []

def get_uuid(ticket_id):
    """Get user ID associated with the ticket."""
    query = "SELECT user_id FROM obf_tickets WHERE id = %s"
    try:
        cursor.execute(query, (ticket_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        st.error(f"Database error: {e}")
        return None

def save_uploaded_file(uploaded_file, folder_path, save_name):
    """Save uploaded file to specified path."""
    if uploaded_file and save_name:
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
    """Verify document based on its type."""
    verify_functions = {
        "Passport": passport_verify,
        "Driving License": license_verify,
        "Payslip": checkpayslip,
        "Bank Statement": checkbankstatement
    }
    verify_func = verify_functions.get(document_type)
    if verify_func:
        return verify_func(file_path, first_name, last_name) if document_type in ["Passport", "Driving License"] else verify_func(file_path)
    return "Invalid document type."

def create_document(doc_path, ticketid, document_type, verification_result, user_id):
    """Create or update document record in database."""
    if user_id is None:
        st.error("User ID not found for the given ticket.")
        return

    document = {
        "Document No": str(uuid.uuid4()),
        "Ticket ID": ticketid,
        "Document Link": doc_path,
        "Document Name": document_type,
        "Verification Response": "",
        "User ID": user_id
    }
    document["Verification Response"] = {1: "Verified", 0: "Reupload", -1: "Incorrect Document"}.get(verification_result, "Unknown")

    check_query = """
    SELECT id FROM obf_documents WHERE ticket_id = %s AND user_id = %s AND document_link LIKE %s
    """
    doc_link_base = os.path.splitext(document["Document Link"])[0]
    try:
        cursor.execute(check_query, (ticketid, user_id, f"{doc_link_base}%"))
        existing_document = cursor.fetchone()

        if existing_document:
            update_query = """
            UPDATE obf_documents
            SET document_name = %s, document_link = %s, verification_response = %s, ticket_id = %s, user_id = %s, modified_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            cursor.execute(update_query, (
                document["Document Name"], document["Document Link"], document["Verification Response"],
                document["Ticket ID"], document["User ID"], existing_document[0]
            ))
        else:
            insert_query = """
            INSERT INTO obf_documents (document_name, document_link, verification_response, ticket_id, user_id, created_at, modified_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(insert_query, (
                document["Document Name"], document["Document Link"], document["Verification Response"],
                document["Ticket ID"], document["User ID"]
            ))
        connection.commit()
    except psycopg2.Error as e:
        st.error(f"Database error: {e}")
        connection.rollback()

def update_tickets(ticket_id, document_responses):
    """Update ticket status based on document verification."""
    all_verified = all(response == "Verified" for response in document_responses)

    try:
        update_query = """
            UPDATE obf_tickets
            SET all_documents_submitted = TRUE
            WHERE id = %s;
        """
        cursor.execute(update_query, (ticket_id,))

        if all_verified:
            update_status_query = """
            UPDATE obf_tickets
            SET status = 'Resolved'
            WHERE id = %s;
            """
            cursor.execute(update_status_query, (ticket_id,))

        connection.commit()
    except psycopg2.Error as e:
        st.error(f"Database error: {e}")
        connection.rollback()

def get_ticket_id_from_url():
    """Extract ticket ID from URL parameters."""
    return st.query_params.get("ticket_id", None)

def main():
    st.title("OBF Document Validator")

    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = None

    # Get ticket_id from URL parameter
    url_ticket_id = get_ticket_id_from_url()

    col1, col2 = st.columns(2)
    with col1:
        # Auto-populate ticket ID if available in URL
        ticket_id = st.text_input("Enter your Ticket ID:", value=url_ticket_id, key="ticket_id")
        
        if ticket_id:
            ticket_type = get_ticket_type(ticket_id)
            if ticket_type:
                dropdown_options = get_dropdown_names(ticket_type)
                if dropdown_options:
                    document_type = st.selectbox(
                        "Select document type", dropdown_options
                    )
                    uploaded_doc = st.file_uploader(
                        "Upload your document", type=["pdf", "png", "jpg", "jpeg"]
                    )
                else:
                    st.error(f"No document types available for ticket type: {ticket_type}")
                    return
            else:
                st.error("Invalid Ticket ID. Please enter a valid Ticket ID.")
                return
        else:
            st.warning("Please enter a Ticket ID to proceed.")
            return

    if uploaded_doc is not None:
        file_type = uploaded_doc.type
        # Preview for image files
        with col2:
            if file_type in ["image/jpeg", "image/jpg", "image/png"]:
                st.text("Image Preview:")
                image = Image.open(uploaded_doc)
                st.image(image, caption="Uploaded Image", use_column_width=True)
            # Preview for PDF files
            elif file_type == "application/pdf":
                st.text("PDF Preview:")
                try:
                    # Use PyMuPDF to render the first page of the PDF
                    pdf_document = fitz.open(stream=uploaded_doc.read(), filetype="pdf")
                    first_page = pdf_document[0]
                    pix = first_page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    st.image(img, caption="First page of PDF", use_column_width=True)
                    
                    # Get additional information about the PDF
                    num_pages = len(pdf_document)
                    st.write(f"Number of pages: {num_pages}")
                except Exception as e:
                    st.error(f"Error processing PDF: {str(e)}")

        if uploaded_doc != st.session_state.last_uploaded_file:
            user_id = get_uuid(ticket_id)
            if user_id:
                file_path = save_uploaded_file(
                    uploaded_doc, document_type, user_id
                )
                st.session_state.last_uploaded_file = uploaded_doc

                verification_result = verify_document(
                    document_type, file_path, "arlington", "beech"
                )
                create_document(file_path, ticket_id, document_type, verification_result, user_id)

                time.sleep(3)
                
                if verification_result == -1:
                    st.error(
                        f"This does not seem to be a valid {document_type.lower()}. Please reupload the requested document."
                    )
                elif verification_result == 0:
                    st.warning(
                        f"Unable to verify your details. Please reupload {document_type.lower()} with correct details."
                    )
                elif verification_result == 1:
                    st.success(f"{document_type} Verification Successful.")
                    st.toast(f"{document_type} verified successfully!", icon="✅")
                else:
                    st.info("Unexpected result from verification.")
            else:
                st.error("Unable to process the document. User ID not found.")
        else:
            st.info("No new file uploaded, or file already saved.")

    if st.button("All documents submitted", key="all_submitted"):
        try:
            document_links, document_responses = get_document_details(ticket_id)
            update_tickets(
                ticket_id=ticket_id,
                document_responses=document_responses
            )
            st.success("Documents submitted successfully!")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
