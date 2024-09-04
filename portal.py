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
from langchain_community.document_loaders import PyPDFLoader
from passport_verify import passport_verify

# Load OpenAI API key from Streamlit secrets
OPENAI_API_KEY = st.secrets["api"]["openai_key"]
openai.api_key = OPENAI_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Initialize OpenAI model
model = ChatOpenAI(model="gpt-4o")

# Define Payslip model
class Payslip(BaseModel):
    Verification: bool = Field(description="True if Document Type is a payslip")
    FirstName: str = Field(description="First Name")
    LastName: str = Field(description="Last Name")
    Date: str = Field(description="Date of the payslip")

# Define BankStatement model
class BankStatement(BaseModel):
    Verification: bool = Field(description="True if document is a bank statement")
    FirstName: str = Field(description="First Name")
    LastName: str = Field(description="Last Name")
    Firstdate: str = Field(description="Date of the first transaction in YYYY-MM-DD")
    Lastdate: str = Field(description="Date of the last transaction in YYYY-MM-DD")

def is_date_less_than_two_months(date_str):
    try:
        input_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."

    current_date = datetime.now()
    two_months_ago = current_date - relativedelta(months=2)
    return input_date > two_months_ago

def is_difference_at_least_sixty_days(date1_str, date2_str):
    try:
        date1 = datetime.strptime(date1_str, "%Y-%m-%d")
        date2 = datetime.strptime(date2_str, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."

    difference = abs((date2 - date1).days)
    return difference >= 60

def convert_to_jpg(file):
    def image_to_base64(image):
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    if file.type == "application/pdf":
        pdf_document = fitz.open(stream=file.read(), filetype="pdf")
        page = pdf_document.load_page(0)
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return image_to_base64(image)

    if file.type in ["image/png", "image/jpeg", "image/jpg"]:
        image = Image.open(file)
        rgb_image = image.convert('RGB')
        return image_to_base64(rgb_image)

def checkpayslip(file):
    image_data = convert_to_jpg(file)
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Verify if the document type is a payslip. Provide Verification as a boolean, First Name, Last Name, and date as YYYY-MM-DD."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
        ]
    )
    structured_model = model.with_structured_output(Payslip)
    response = structured_model.invoke([message])
    if not response.Verification:
        return -1  # Incorrect Document Uploaded
    return 1 if is_date_less_than_two_months(response.Date) else -1

def checkbankstatement(file):
    text = extract_text(file)
    structured_model = model.with_structured_output(BankStatement)
    response = structured_model.invoke(text)
    if not response.Verification:
        return -1  # Incorrect Document Uploaded
    return 1 if is_difference_at_least_sixty_days(response.Firstdate, response.Lastdate) else -1

def extract_text(file):
    file.seek(0)  # Reset file pointer to the beginning
    if file.type == "application/pdf":
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    else:
        image = Image.open(file)
        text = "Image file uploaded (text extraction not implemented)"
    return text

def main():
    st.title("Document Upload Portal")

    # Allow the user to select the document type
    document_type = st.selectbox("Select document type", ["Payslip", "Bank Statement", "Passport"])

    # Allow the user to upload the document
    uploaded_doc = st.file_uploader("Upload your document", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded_doc is not None:
        if document_type == "Payslip":
            result = checkpayslip(uploaded_doc)
        elif document_type == "Bank Statement":
            result = checkbankstatement(uploaded_doc)
        elif document_type == "Passport":
            # Save the uploaded image temporarily
            temp_file_path = f"/tmp/{uploaded_doc.name}"
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_doc.getbuffer())

            # Call the passport_verify function
            result = passport_verify(temp_file_path, first_name, last_name)

            # Remove the temporary file
            os.remove(temp_file_path)

        # Display the result
        st.subheader("Verification Result:")
        if result == -1:
            st.write("Oops!! This seems to be the wrong document. Please try again")
        elif result == 0:
            st.write("Sorry, please upload a better image for processing.")
        elif result == 1:
            st.write("Thank you for providing the document. We will update you shortly!")

        st.success("Document uploaded and processed successfully!")

if __name__ == "__main__":
    main()
