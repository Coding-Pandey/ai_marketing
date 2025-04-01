import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from S3_bucket.S3_client import s3
import os
from tempfile import TemporaryDirectory
from botocore.exceptions import ClientError
from fastapi import HTTPException
import platform
import docx
try:
    from win32com import client
    WINDOWS_AVAILABLE = platform.system() == "Windows"
except ImportError:
    WINDOWS_AVAILABLE = False

S3_BUCKET_NAME = os.environ.get("BUCKET_NAME")
user_folder = "User/"


def fetch_document_from_s3(user_id: str, category: str) -> dict:
    """
    Fetch document from S3 bucket
    """
    try:
        prefix = f"{user_id}/{category}"
        # print(prefix)
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        # print(response)
   
        if "Contents" not in response or not response["Contents"]:
            return {"documents": []}
        
       
        # documents = [
        #         obj["Key"] for obj in response["Contents"]
        #         if obj["Key"].endswith((".doc", ".docx", ".pdf")) 
        #     ]
        documents =[obj["Key"] for obj in response["Contents"]]
        return {"documents": documents}
        

    except ClientError as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch document from S3: {str(e)}")
    

# da = fetch_document_from_s3("User", "Buyer persona")    
# print(da)

data = {'Buyer persona': 'User/Buyer persona/Buyer_Persona_.docx', 
        'Tone of voice': 'User/Tone of voice/Tone_of_voice.docx',
          'Brand identity': 'User/Brand identity/Brand_identity.docx',
            'Offering': 'User/Offering/Offering.docx'}

def extract_text_from_file(file_path: str) -> str:
    """Extract text from .docx or .doc files based on file extension."""
    if file_path.lower().endswith('.docx'):
        # Handle .docx files
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n".join(full_text)
    
    elif file_path.lower().endswith('.doc'):
        # Handle .doc files
        if WINDOWS_AVAILABLE:
            # Use pywin32 on Windows
            word = client.Dispatch("Word.Application")
            word.Visible = False  # Run in background
            doc = word.Documents.Open(file_path)
            text = doc.Content.Text
            doc.Close()
            word.Quit()
            return text.strip()
        else:
            # Fallback for non-Windows: Suggest conversion (or implement it)
            raise NotImplementedError(
                "Extraction of .doc files is only supported on Windows with pywin32. "
                "Alternatively, convert .doc to .docx using LibreOffice: "
                "'libreoffice --headless --convert-to docx file.doc'"
            )
    else:
        raise ValueError(f"Unsupported file type: {file_path}")

def download_document(data: dict) -> dict:
    extracted_texts = {}
    # Download each file
    with TemporaryDirectory() as temp_dir:
        for folder, file_path in data.items():
            # Extract the file name from the path for local saving
            file_name = file_path.split('/')[-1]
            local_path = os.path.join(temp_dir, file_name)
            print(f"Downloading {file_name} from {S3_BUCKET_NAME}/{file_path}...")
            
            # Download the file
            s3.download_file(S3_BUCKET_NAME, file_path, local_path)
            print(f"Downloaded {file_name} successfully!")
 
            try:
                text = extract_text_from_file(local_path)
                extracted_texts[folder] = text
            except Exception as e:
                extracted_texts[folder] = f"Error extracting text: {str(e)}"

    print("All files downloaded.")
    print(extracted_texts)
    return extracted_texts

# data = download_document(data)
# print(data)