from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Form, Query
from fastapi.responses import JSONResponse
from auth.models import SourceFileCategory, SourceFileContent
from auth.auth import get_db
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session
from utils import verify_jwt_token, check_api_limit
from docx import Document
from io import BytesIO



router = APIRouter()

@router.post("/upload_and_parse/")
async def upload_and_parse_file(
    category: SourceFileCategory = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    # Extract text from file
    file_ext = file.filename.lower().split(".")[-1]
    file_bytes = await file.read()

    if file_ext == "docx":
        
        doc = Document(BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    json_data = {category: text}
    # Save text to DB
    record = SourceFileContent(
        file_name=file.filename,
        category=category,
        uploaded_by=user_id,
        extracted_text=text
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"message": "File content saved", "record_id": record.id}