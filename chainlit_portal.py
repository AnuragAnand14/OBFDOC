import chainlit as cl
import os
import shutil

# Define the document types and their corresponding folders
DOCUMENT_TYPES = {
    "passport": "passports",
    "driving license": "driving_licenses",
    "payslip": "payslips",
    "bank statement": "bank_statements"
}

def create_folders():
    for folder in DOCUMENT_TYPES.values():
        os.makedirs(folder, exist_ok=True)

async def save_file(file, document_type):
    folder = DOCUMENT_TYPES[document_type]
    file_extension = os.path.splitext(file.name)[1]
    save_path = os.path.join(folder, f"{document_type}{file_extension}")
    
    # Use cl.make_async to perform file operations asynchronously
    await cl.make_async(shutil.copy)(file.path, save_path)
    
    return save_path

@cl.on_chat_start
async def main():
    create_folders()
    
    await cl.Message(
        content="Welcome to the Multi-Document Upload Portal. Please upload the following documents:",
        author="system"
    ).send()

    uploaded_documents = {}

    for doc_type in DOCUMENT_TYPES.keys():
        files = await cl.AskFileMessage(
            content=f"Please upload your {doc_type} (PDF, PNG, JPG, or JPEG)",
            accept=["application/pdf", "image/png", "image/jpeg"]
        ).send()

        if files:
            file = files[0]
            save_path = await save_file(file, doc_type)
            uploaded_documents[doc_type] = save_path
            await cl.Message(content=f"{doc_type.capitalize()} uploaded successfully and saved in {save_path}").send()
        else:
            await cl.Message(content=f"No {doc_type} was uploaded. You can upload it later.").send()

    if uploaded_documents:
        await cl.Message(content="Thank you for uploading your documents. If you need to upload any missing documents or make changes, please let me know.").send()
    else:
        await cl.Message(content="No documents were uploaded. You can upload them at any time by specifying the document type.").send()

@cl.on_message
async def handle_message(message: cl.Message):
    if message.content.lower() in DOCUMENT_TYPES:
        doc_type = message.content.lower()
        files = await cl.AskFileMessage(
            content=f"Please upload your {doc_type} (PDF, PNG, JPG, or JPEG)",
            accept=["application/pdf", "image/png", "image/jpeg"]
        ).send()

        if files:
            file = files[0]
            save_path = await save_file(file, doc_type)
            await cl.Message(content=f"{doc_type.capitalize()} uploaded successfully and saved in {save_path}").send()
        else:
            await cl.Message(content=f"No {doc_type} was uploaded. You can try again later.").send()
    elif message.elements:
        for element in message.elements:
            if isinstance(element, cl.File):
                await cl.Message(content="Please specify the document type for this upload (passport, driving license, payslip, or bank statement).").send()
                return
    else:
        await cl.Message(content="To upload a document, please specify the document type (passport, driving license, payslip, or bank statement) and then use the file upload button.").send()

if __name__ == "__main__":
    cl.run()