import os
import pypandoc
from docx import Document
from io import BytesIO
from docx import Document
import tempfile
# def extract_text_from_docx(file_path):
#     """Extracts text from a .docx file."""
#     doc = Document(file_path)
#     return '\n'.join([para.text for para in doc.paragraphs])

# def extract_text_from_doc(file_path):
#     """Extracts text from a .doc file using Pandoc (cross-platform)."""
#     return pypandoc.convert_file(file_path, 'plain')

# def convert_doc_to_text(file_path):
#     """Converts a .doc or .docx file into text."""
#     if not os.path.exists(file_path):
#         raise FileNotFoundError("File not found.")
    
#     file_ext = os.path.splitext(file_path)[1].lower()
#     if file_ext == '.docx':
#         return extract_text_from_docx(file_path)
#     elif file_ext == '.doc':
#         return extract_text_from_doc(file_path)
#     else:
#         raise ValueError("Unsupported file format. Use .doc or .docx")


def extract_text_from_docx_bytes(file_bytes):
    """Extracts text from a .docx file in bytes."""
    doc = Document(BytesIO(file_bytes))
    return '\n'.join([para.text for para in doc.paragraphs])

def extract_text_from_doc_bytes(file_bytes):
    """Extracts text from a .doc file in bytes using Pandoc."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.doc') as temp_file:
        temp_file.write(file_bytes)
        temp_file_path = temp_file.name
    try:
        return pypandoc.convert_file(temp_file_path, 'plain')
    finally:
        os.unlink(temp_file_path)

def convert_doc_to_text(file_bytes, filename):
    """Converts a .doc or .docx file in bytes into text."""
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext == '.docx':
        return extract_text_from_docx_bytes(file_bytes)
    elif file_ext == '.doc':
        return extract_text_from_doc_bytes(file_bytes)
    else:
        raise ValueError("Unsupported file format. Use .doc or .docx")
# Example usage
# text = convert_doc_to_text(r"C:\Users\nickc\OneDrive\Desktop\AI marketing\doc\Plug_%26_Play%2C_Grow_-_campaing (1).docx")
# print(text)
