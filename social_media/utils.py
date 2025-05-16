import os
import pypandoc
from docx import Document
from io import BytesIO
from docx import Document
import tempfile
from auth.auth import get_db
from auth.models import SocialMediaFile
from datetime import datetime, timedelta
from typing import Union
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

import re
import emoji

def clean_post(text, remove_emojis=True, remove_hashtags=True):
    if remove_emojis == False:
        text = ''.join(char for char in text if not emoji.is_emoji(char))

    if remove_hashtags == False:
        text = re.sub(r'#\w+', '', text)

    return text.strip()


def clean_post_list(data_list, remove_emojis=True, remove_hashtags=True): 
    cleaned = []
    for item in data_list:
        new_item = {}
        for key, val in item.items():
            if isinstance(val, list) and all(isinstance(v, str) for v in val):
                new_item[key] = [
                    clean_post(
                        text,
                        remove_emojis=remove_emojis,
                        remove_hashtags=remove_hashtags,
                    ) for text in val
                ]
            else:
                new_item[key] = val  # leave non-list or non-str values untouched
        cleaned.append(new_item)
    return cleaned


def upload_socialmedia_table( uuid: str, user_id: int, file_name: str, linkedIn: Union[dict, list], facebook_post: Union[dict, list], twitter_post: Union[dict, list]):
    db = next(get_db()) 
    try:
        new_file = SocialMediaFile(
            user_id=user_id,
            file_name=file_name,
            uuid=uuid,
            linkedIn_post = linkedIn,
            facebook_post = facebook_post,
            twitter_post  = twitter_post,
            last_reset = datetime.utcnow()
        )

        
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        return {
            "id": new_file.id,  # Assuming an id field exists
            "user_id": new_file.user_id,
            "file_name": new_file.file_name,
            "uuid": new_file.uuid,
            "linkedIn_post": new_file.linkedIn_post,
            "facebook_post": new_file.facebook_post,
            "twitter_post": new_file.twitter_post,
            "last_reset": new_file.last_reset.isoformat() if new_file.last_reset else None
        }  # You can return the created object if needed

    except Exception as e:
        db.rollback()
        print(str(e))
        raise Exception(f"Error storing SEO file in table: {str(e)}")
    finally:
        db.close() 