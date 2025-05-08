import io
import pdfplumber
from typing import List

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts text from a PDF file represented as bytes.

    Args:
        pdf_bytes (bytes): Binary content of the PDF.

    Returns:
        str: All extracted text from all pages concatenated.
    """
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text.strip()
