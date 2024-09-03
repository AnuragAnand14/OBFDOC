import streamlit as st
import pytesseract
from PIL import Image
import PyPDF2

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

def verify_document(text, customer_data):
    required_fields = ["Passport Country", "Expiry Date", "Passport Number", "F. Name", "L. Name"]
    for field in required_fields:
        if field.lower() not in text.lower():
            return "Oops! This seems to be the wrong document. Please try again."
    
    if len(text) < 50:  # Arbitrary threshold, adjust as needed
        return "Sorry, please upload a better image for processing."
    
    return "Thank you for providing the document. We will update you shortly!"

def main():
    st.title("Document Verification System - Customer Portal")

    upload_link = st.text_input("Enter your unique upload link")
    if st.button("Go to Upload Portal") and upload_link:
        st.markdown(f"[Click here to upload your document]({upload_link})", unsafe_allow_html=True)
    
    uploaded_doc = st.file_uploader("Upload your document", type=["pdf", "png", "jpg", "jpeg"])
    
    if uploaded_doc is not None and upload_link:
        # Extract text from the document
        extracted_text = extract_text(uploaded_doc)
        
        # Verify the document
        result = verify_document(extracted_text, {})  # Pass customer data here if available
        
        st.write(result)
        
        # Here you would typically update the status in a database
        # For this example, we'll just display a success message
        st.success("Document uploaded successfully!")

if __name__ == "__main__":
    main()
