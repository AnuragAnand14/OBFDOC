import streamlit as st
from PIL import Image
import PyPDF2
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import openai
import fitz
import base64
from io import BytesIO
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
#from langchain_community.document_loaders import PyPDFLoader
from passport_verify import passport_verify
from license_verify import license_verify
from income_verify import checkbankstatement,checkpayslip
import uuid
import pandas as pd



def get_dropdown_names(TicketType) :
    if TicketType == "Income" :
        return ["Payslip", "Bank Statement"]
    elif TicketType == "Fraud" :
        return ["Passport", "Driving License"]
    elif TicketType == "Both":
        return ["Payslip", "Bank Statement", "Passport", "Driving License"]

def get_ticket_type(ticket_id, excel_file):
    # Load the Excel file
    df = pd.read_excel(excel_file)
    
    # Check if the Ticket ID exists in the DataFrame
    if ticket_id in df['Ticket No'].values:
        # Retrieve the Ticket Type based on the Ticket ID
        ticket_type = df.loc[df['Ticket No'] == ticket_id, 'Ticket Type'].values[0]
        return ticket_type
    else:
        return "Ticket ID not found."

def get_document_details(csv_file, ticket_id):
    df = pd.read_csv(csv_file)
    


# Filter the DataFrame based on the given Ticket No
    filtered_df = df[df["Ticket No"] == ticket_id]

# Fetch the list of Document Responses and Document Links
    document_responses = filtered_df["Document Response"].tolist()
    document_links = filtered_df["Document Link"].tolist()

    return document_links, document_responses

def get_uuid(ticket_id, excel_file):
    df = pd.read_excel(excel_file)
    
    # Check if the Ticket ID exists in the DataFrame
    if ticket_id in df['Ticket No'].values:
        # Retrieve the Ticket Type based on the Ticket ID
        uuid = df.loc[df['Ticket No'] == ticket_id, 'UUID'].values[0]
        return uuid
    else:
        return "UUIID not found."

def save_uploaded_file(uploaded_file, folder_path, save_name):
    """
    Save an uploaded file to a specified folder with a given name.
    If the save_name does not have an extension, the function adds the original file's extension.
    
    Parameters:
        uploaded_file (UploadedFile): The file uploaded by the user.
        folder_path (str): The folder where the file should be saved.
        save_name (str): The name to save the file as (without extension).
        
    Returns:
        str: The full file path where the file was saved.
    """
    if uploaded_file is not None and save_name:
        # Extract the original file extension
        original_filename = uploaded_file.name
        _, file_extension = os.path.splitext(original_filename)
        
        # Append the extension to save_name if not provided
        if not os.path.splitext(save_name)[1]:  # Check if save_name has no extension
            save_name += file_extension
        
        # Ensure the folder exists
        os.makedirs(folder_path, exist_ok=True)
        
        # Full path to save the file
        file_path = os.path.join(folder_path, save_name)
        
        # Save the file to the specified location
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return file_path
    return None

def verify_document(document_type,file_path,first_name,last_name):
    if document_type == "Passport":
        result = passport_verify(file_path,first_name,last_name)
    elif document_type == "Driving License":
        result = license_verify(file_path,first_name,last_name)
    elif document_type=="Payslip":
        result = checkpayslip(file_path)
    elif document_type=="Bank Statement":
        result = checkbankstatement(file_path)
    
    else:
        result = "Invalid document type."
    return result


def update_tickets(csv_file, ticket_id, document_link, document_response):

# Load the tickets CSV file into a DataFrame
    tickets_df = pd.read_csv(csv_file)
        
        # Check if 'Ticket No' column exists
    if 'Ticket No' not in tickets_df.columns:
        raise ValueError("The CSV file must contain a 'Ticket No' column.")
        
        # Check if the ticket_id exists in the DataFrame
    if ticket_id not in tickets_df["Ticket No"].values:
        raise ValueError(f"Ticket ID {ticket_id} not found in the CSV file.")
        
        # Convert lists to strings for storage in CSV
    document_responses_str = ', '.join(map(str, document_response))
    document_links_str = ', '.join(map(str, document_link))
        
        # Update the 'Document Response' and 'Document Link' columns
    mask = tickets_df["Ticket No"] == ticket_id
        
        # Debug: Print out which rows are being updated
    print(f"Updating rows for Ticket ID {ticket_id}:")
    print(tickets_df[mask])
        
    tickets_df.loc[mask, "Document Response"] = document_responses_str
    tickets_df.loc[mask, "Document Link"] = document_links_str
        
        # Determine the status based on the document responses
    status = "All Documents Verified" if all(response == "Verified" for response in document_response) else "Pending Verified Documents"
        
        # Update the 'Status' column
    tickets_df.loc[mask, "Status"] = status
        
        # Save the updated tickets DataFrame back to the CSV
    tickets_df.to_csv(csv_file, index=False)
        
    print("Tickets CSV updated successfully!")

def remove_extension(file_path):
    """Helper function to remove file extension from the file path."""
    return os.path.splitext(file_path)[0]

def create_document(doc_path, ticketid, document_type, verification_result):
    document = {
        "Document No": str(uuid.uuid4()),
        "Ticket No": ticketid,
        "Document Link": doc_path,
        "Document Type" : document_type,
        "Document Response": "",
    }
    if verification_result == 1:
        document["Document Response"] = "Verified"
    elif verification_result == 0:
        document["Document Response"] = "Reupload"
    elif verification_result == -1:
        document["Document Response"] = "Incorrect Document"
    
    df = pd.DataFrame([document])

    file_path = "Document_Database.csv"

    if os.path.exists(file_path):
        # Load existing CSV into DataFrame
        existing_df = pd.read_csv(file_path)
        
        # Check if the same document link or document ID exists, and update it
        existing_df['Doc Link Base'] = existing_df['Document Link'].apply(remove_extension)
        df['Doc Link Base'] = df['Document Link'].apply(remove_extension)

        # Check for duplicates based on the base name of the document link
        merged_df = pd.concat([existing_df, df]).drop_duplicates(subset=["Doc Link Base"], keep='last')
        
        # Drop the temporary 'Doc Link Base' column
        merged_df = merged_df.drop(columns=["Doc Link Base"])
        
        # Save the updated DataFrame back to the CSV
        merged_df.to_csv(file_path, index=False)
    else:
        # If the file doesn't exist, just use the new DataFrame
        merged_df = df

    # Save the updated DataFrame to CSV, overwriting the existing file if necessary
    merged_df.to_csv(file_path, index=False)
def main():
    st.title("Document Upload Portal")
    
   

# Initialize session state to track the uploaded file
    if 'last_uploaded_file' not in st.session_state:
            st.session_state.last_uploaded_file = None

    ticket_id = st.text_input("Enter your Ticket ID:")

    excel_file_path = 'ticket_updates.xlsx'

    ticket_type = get_ticket_type(ticket_id, excel_file_path)

    document_type = st.selectbox("Select document type", get_dropdown_names(ticket_type))

# Allow the user to upload the document
    uploaded_doc = st.file_uploader("Upload your document", type=["pdf", "png", "jpg", "jpeg"])

# Only save the file if a new file has been uploaded
    if uploaded_doc is not None and uploaded_doc != st.session_state.last_uploaded_file:
        file_path = save_uploaded_file(uploaded_doc, document_type, get_uuid(ticket_id, excel_file_path))
        st.session_state.last_uploaded_file = uploaded_doc  # Update the session state with the latest uploaded file
        st.success(f"File saved successfully  ")
        print(file_path)

        verification_result = verify_document(document_type,file_path,"Arlington","Beech")
        
        create_document(file_path, ticket_id, document_type, verification_result)
        doc_csv_file = "Document_Database.csv"
        
        
        document_link, document_responses = get_document_details(doc_csv_file, ticket_id)
        
        
        tick_csv_file = "Ticket_Database.csv"
        update_tickets(csv_file=tick_csv_file, ticket_id= ticket_id, document_link=document_link, document_response=document_responses)
    # Show different prompts based on the result of passport_verify()
        if verification_result == -1:
            st.error(" Please upload the correct document.")

        
        elif verification_result == 0 :
            st.warning("Please reupload")
            
        
        
        elif verification_result == 1:
            st.success(f"{document_type} Verification successful.")
            
        
        
        else:
            st.info("Unexpected result from passport verification.")

    
    
    else:
        st.info("No new file uploaded, or file already saved.")

    



if __name__ == "__main__":
    main()
