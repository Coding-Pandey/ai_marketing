from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Form, Query
from fastapi.responses import JSONResponse
from auth.models import SourceFileCategory, SourceFileContent
from auth.auth import get_db
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session
from utils import verify_jwt_token, check_api_limit
from docx import Document
from io import BytesIO
import uuid
import datetime


router = APIRouter()

@router.get("/uploaded_files")
async def get_uploaded_files(user_id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    user_id = user_id[1]
    files = db.query(SourceFileContent).filter(SourceFileContent.user_id == user_id).all()
    if not files:
        return []
    files = [
        {
            "file_name": file.file_name,
            "category": file.category,
            "uuid_id": file.uuid_id,
        } for file in files
    ]

    return {"uploaded_files": files}


@router.delete("/delete_Source_file/{uuid_id}")
async def delete_source_file(uuid_id: str, user_id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    user_id = user_id[1]
    file_record = db.query(SourceFileContent).filter(
        SourceFileContent.uuid_id == uuid_id,
        SourceFileContent.user_id == user_id
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    db.delete(file_record)
    db.commit()
    flag_modified(file_record, "file_data")  # Mark file_data as modified if needed

    return {"message": "File deleted successfully"}


@router.post("/upload_and_parse")
async def upload_and_parse_file(
    category: SourceFileCategory = Form(...),
    file: UploadFile = File(...),
    file_name: str = Form(...),
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    # Extract text from file
    user_id = user_id[1]

    file_ext = file.filename.lower().split(".")[-1]
    file_bytes = await file.read()

    if file_ext == "docx":
        
        doc = Document(BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
        print(text)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    print(category, file.filename, user_id)
    json_data = {category.name: text}
    uuid_id = str(uuid.uuid4().hex)
    # Save text to DB
    record = SourceFileContent(
        user_id=user_id,
        uuid_id=uuid_id,
        file_name=file_name,
        category=category,
        uploaded_at=datetime.datetime.now(),
        # extracted_text=text
        file_data = json_data
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"message": "File content saved", "record_id": record.id}

