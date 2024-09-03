import streamlit as st
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
        # Note: We're not using pytesseract here as it was removed from the requirements
        text = "Image file uploaded (text extraction not implemented)"
    return text

def main():
    st.title("Document Upload Portal")

    uploaded_doc = st.file_uploader("Upload your document", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded_doc is not None:
        # Extract text from the document (for demonstration purposes)
        extracted_text = extract_text(uploaded_doc)

        # Display a preview of the extracted text
        st.subheader("Document Preview:")
        st.text(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)

        # Here you would typically save the document or process it further
        # For this example, we'll just display a success message
        st.success("Document uploaded successfully!")

        # You can add additional processing or storage logic here

if __name__ == "__main__":
    main()
