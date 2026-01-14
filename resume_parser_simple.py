import PyPDF2
from docx import Document
import re

def extract_text_from_pdf(file):
    """Extract text from PDF file or file object"""
    try:
        if hasattr(file, 'read'):  # File-like object
            reader = PyPDF2.PdfReader(file)
        else:  # File path
            reader = PyPDF2.PdfReader(file)
        
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        return clean_text(text)
    except Exception as e:
        print(f"PDF error: {e}")
        return ""

def extract_text_from_docx(file):
    """Extract text from DOCX file or file object"""
    try:
        if hasattr(file, 'read'):  # File-like object
            doc = Document(file)
        else:  # File path
            doc = Document(file)
        
        text = "\n".join([para.text for para in doc.paragraphs])
        return clean_text(text)
    except Exception as e:
        print(f"DOCX error: {e}")
        return ""

def clean_text(text):
    """Clean text by removing extra spaces and special chars"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text.strip()