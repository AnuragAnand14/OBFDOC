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


def update_document_attributes(excel_path, verification_result,uuid):
    
    df= pd.read_excel(excel_path)
    row_to_update = df[df['UUID'] == uuid]
    df['Document Response'] = df['Document Response'].astype('object')

    # Check if the row exists
    if not row_to_update.empty:
        # Update 'document_response' based on 'result'
        if verification_result == 1:
            df.loc[df['UUID'] == uuid, 'Document Response'] = 'Verified'
            df.loc[df['UUID'] == uuid, 'Status'] = 'Done'  # Also update 'Status' if result is 1
            print("updated")
        elif verification_result== 0:
            df.loc[df['UUID'] == uuid, 'Document Response'] = 'Reupload'
        elif verification_result== -1:
            df.loc[df['UUID'] == uuid, 'Document Response'] = 'Incorrect Document'

        print(df)
        csv_output_path="new.csv"
        df.to_csv(csv_output_path, index=False)        
    else:
        print(f"No row found with uuid: {uuid}")








def main():
    st.title("Document Upload Portal")
    
   

# Initialize session state to track the uploaded file
    if 'last_uploaded_file' not in st.session_state:
            st.session_state.last_uploaded_file = None

    ticket_id = st.text_input("Enter your Ticket ID:")

    excel_file_path = '/Users/Angad.Kwatra/Desktop/OBF/OBFDOC/ticket_updates.xlsx'

    ticket_type = get_ticket_type(ticket_id, excel_file_path)

    document_type = st.selectbox("Select document type", get_dropdown_names(ticket_type))

# Allow the user to upload the document
    uploaded_doc = st.file_uploader("Upload your document", type=["pdf", "png", "jpg", "jpeg"])

# Only save the file if a new file has been uploaded
    if uploaded_doc is not None and uploaded_doc != st.session_state.last_uploaded_file:
        file_path = save_uploaded_file(uploaded_doc, document_type, get_uuid(ticket_id, excel_file_path))
        st.session_state.last_uploaded_file = uploaded_doc  # Update the session state with the latest uploaded file
        st.success(f"File saved successfully at {file_path}")
        print(file_path)

        verification_result = verify_document(document_type,file_path,"Arlington","Beech")
        update_document_attributes(excel_file_path,verification_result,get_uuid(ticket_id,excel_file_path))

        
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