import os
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
# For Excel, you might use openpyxl or pandas. For PPTX, python-pptx.
# These are just examples for PDF and DOCX.

SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    # Add more types as needed, e.g., text/plain, .pptx, .xlsx
}

def extract_text_from_file(file_path: str, mime_type: str) -> str:
    """Extracts text from a supported file type."""
    extracted_text = ""
    file_extension = SUPPORTED_MIME_TYPES.get(mime_type)

    if not file_extension:
        return "Unsupported file type for text extraction."

    try:
        if file_extension == "pdf":
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    extracted_text += page.extract_text() + "\n"
        elif file_extension == "docx":
            doc = DocxDocument(file_path)
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"
        # Add handlers for other file types (txt, pptx, xlsx) here
        # elif file_extension == "txt":
        #     with open(file_path, "r", encoding='utf-8') as f:
        #         extracted_text = f.read()
        else:
            return f"Text extraction for {file_extension} not implemented yet."
        
        if not extracted_text.strip():
             return "No text could be extracted from the document, or document is empty."
        return extracted_text.strip()
    
    except Exception as e:
        print(f"Error extracting text from {file_path} ({mime_type}): {e}")
        return f"Error during text extraction: {str(e)}"

# Example usage (can be tested independently):
# if __name__ == '__main__':
#     # Create dummy files for testing
#     # test_pdf_path = "dummy.pdf" # Create a real PDF for testing
#     # test_docx_path = "dummy.docx" # Create a real DOCX for testing
#     # if os.path.exists(test_pdf_path):
#     #     print(f"--- PDF Text ---\n{extract_text_from_file(test_pdf_path, 'application/pdf')}")
#     # if os.path.exists(test_docx_path):
#     #     print(f"--- DOCX Text ---\n{extract_text_from_file(test_docx_path, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}") 