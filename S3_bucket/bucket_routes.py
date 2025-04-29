from fastapi import APIRouter, UploadFile, File, HTTPException , Form,Depends, Request
from S3_bucket.S3_upload import upload_file_to_s3,upload_title_url
from sqlalchemy.orm import Session
from S3_bucket.fetch_document import fetch_document_from_s3, fetch_seo_cluster_file,fetch_ppc_cluster_file
from fastapi.responses import JSONResponse
from fastapi import Body
from typing import Annotated
from utils import verify_jwt_token, check_api_limit
from S3_bucket.utile import convert_into_csvdata, upload_seo_table
from S3_bucket.delete_doc import seo_cluster_delete_document
from auth.models import SEOFile, SEOCSV, PPCFile, PPCCSV
from auth.auth import get_db
from botocore.exceptions import ClientError
import pandas as pd
import uuid
import io
import json
router = APIRouter()
from pydantic import BaseModel
class UUIDRequest(BaseModel):
    uuid: str
#S3 bucket document upload
@router.post("/uploadfile")
async def create_upload_file(category: Annotated[str, Form()],
                             file: UploadFile = File(...)):
    
    VALID_CATEGORIES = {"Buyer persona", "Tone of voice", "Brand identity", "Offering"}   
    try:
        # Validate category
        print(category)
        if category not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"
            )

        # Read file content
        file_content = await file.read()
        
        # Validate file size (e.g., max 10MB)

        max_size = 10 * 1024 * 1024  
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds maximum limit of 10MB"
            )

        # Get filename and ensure it's safe
        filename = file.filename
        if not filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )

        # Upload to S3
        s3_path = upload_file_to_s3(file_content, filename, category)

        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "s3_path": s3_path,
                "filename": filename,
                "category": category
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/seo_Clusterfiles_list")
async def seo_csv_documents(db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    try:
        user_id = int(id[1])  # Extract user_id from the JWT token
        seo_files = db.query(SEOFile).filter(SEOFile.user_id == user_id).all()
        file_count = len(seo_files)

        if not seo_files:
            raise HTTPException(status_code=404, detail="No files found for the user")

        # Fetch the SEOCSV record for last_reset value
        seo_csv_record = db.query(SEOCSV).filter(SEOCSV.user_id == user_id).first()

        last_reset = seo_csv_record.last_reset if seo_csv_record else None

        if seo_csv_record:
        
            seo_csv_record.file_count = file_count
            seo_csv_record.call_count = file_count
            db.commit()

        # Include last_reset in each file entry
        result = [
            {
                "file_name": seo_file.file_name,
                "uuid": seo_file.uuid,
                "upload_time": seo_file.upload_time,
                "last_reset": last_reset
            }
            for seo_file in seo_files
        ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ppc_Clusterfiles_list")
async def ppc_csv_documents(db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    try:
        user_id = int(id[1])  # Extract user_id from the JWT token
        ppc_files = db.query(PPCFile).filter(PPCFile.user_id == user_id).all()
        file_count = len(ppc_files)

        if not ppc_files:
            raise HTTPException(status_code=404, detail="No files found for the user")

        # Fetch the PPCCSV record for last_reset value
        ppc_csv_record = db.query(PPCCSV).filter(PPCCSV.user_id == user_id).first()

        last_reset = ppc_csv_record.last_reset if ppc_csv_record else None

        if ppc_csv_record:
            # Update file_count and call_count
            ppc_csv_record.file_count = file_count
            ppc_csv_record.call_count = file_count
            db.commit()

        # Include last_reset in each file entry
        result = [
            {
                "file_name": ppc_file.file_name,
                "uuid": ppc_file.uuid,
                "upload_time": ppc_file.upload_time,
                "last_reset": last_reset
            }
            for ppc_file in ppc_files
        ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/seo_cluster_uploadfile")
async def csv_seo_upload_file(json_data: dict = Body(...),
    id: str = Depends(verify_jwt_token),
    user=Depends(check_api_limit("seo_csv"))):
      
    try:
        
        # Read file content
        file_content = json_data.get("data", [])

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
        
        # data = convert_into_csvdata(file_content)
        # df = pd.DataFrame(data)
        # print(df.head())
        json_str = json.dumps(file_content)

        # Create a buffer for the JSON data
        json_buffer = io.StringIO(json_str)
        json_buffer.seek(0)

        # csv_buffer = io.StringIO()
        # df.to_csv(csv_buffer, index=False)
        # csv_buffer.seek(0)  # Go to start of buffer

        unique_id = uuid.uuid4().hex
        
        max_size = 10 * 1024 * 1024  
        if json_buffer.tell() > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds maximum limit of 10MB"
            )

   
        filename = json_data.get("fileName", None)

        if not filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )

     
        your_tuple = id
        user_id = your_tuple[1] 
        user_folder = f"User_{user_id}"
        # print(user_folder)
        # print(user_id)
        folder_name = "seo_clustering_data"

        s3_path = upload_title_url(user_folder, json_buffer.getvalue(), str(unique_id), folder_name)

        if s3_path is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to S3"
            )
        
        if s3_path:
            upload_seo_table(str(unique_id), user_id, filename)

        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "s3_path": s3_path,
                "filename": filename,
                "category": folder_name
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    
@router.post("/ppc_cluster_uploadfile")
async def csv_ppc_upload_file(json_data: dict = Body(...),
    id: str = Depends(verify_jwt_token),
    user=Depends(check_api_limit("ppc_csv"))):
      
    try:
        
        # Read file content
        file_content = json_data.get("data", [])

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
        
        # data = convert_into_csvdata(file_content)
        # df = pd.DataFrame(data)
        # print(df.head())
        json_str = json.dumps(file_content)

        # Create a buffer for the JSON data
        json_buffer = io.StringIO(json_str)
        json_buffer.seek(0)

        # csv_buffer = io.StringIO()
        # df.to_csv(csv_buffer, index=False)
        # csv_buffer.seek(0)  # Go to start of buffer

        unique_id = uuid.uuid4().hex
        
        max_size = 10 * 1024 * 1024  
        if json_buffer.tell() > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds maximum limit of 10MB"
            )

   
        filename = json_data.get("fileName", None)

        if not filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )

     
        your_tuple = id
        user_id = your_tuple[1] 
        user_folder = f"User_{user_id}"
        # print(user_folder)
        # print(user_id)
        folder_name = "ppc_clustering_data"

        s3_path = upload_title_url(user_folder, json_buffer.getvalue(), str(unique_id), folder_name)

        if s3_path is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to S3"
            )
        
        if s3_path:
            upload_seo_table(str(unique_id), user_id, filename)

        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "s3_path": s3_path,
                "filename": filename,
                "category": folder_name
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    
@router.post("/seo_cluster_fetch_data")
async def seo_fetch_document(request: UUIDRequest, id: str = Depends(verify_jwt_token)):

    try:
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = request.uuid
        data = fetch_seo_cluster_file(user_id, uuid)
        if not data:
            raise HTTPException(status_code=404, detail="No documents found for the user")
        json_data = json.loads(data["documents"])
        return json_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/ppc_cluster_fetch_data")
async def ppc_fetch_document(request: UUIDRequest, id: str = Depends(verify_jwt_token)):

    try:
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = request.uuid
        data = fetch_ppc_cluster_file(user_id, uuid)
        if not data:
            raise HTTPException(status_code=404, detail="No documents found for the user")
        json_data = json.loads(data["documents"])
        return json_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.delete("/seo_cluster_delete_document")
async def ppc_delete_document(request: UUIDRequest, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = request.uuid
        success = seo_cluster_delete_document(uuid, user_id)
        if success:
            # 2. Delete DB record
            user_id = int(id[1]) 
            file_record = db.query(SEOFile).filter_by(user_id=user_id, uuid=uuid).first()

            if file_record:
                db.delete(file_record)
                db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document deleted successfully",
                "uuid": uuid
            }
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete documents: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/ppc_cluster_delete_document")
async def ppc_delete_document(request: UUIDRequest, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        user_id = str(id[1]) 
        uuid = request.uuid
        success = seo_cluster_delete_document(uuid, user_id)
        if success:
        
            user_id = int(id[1]) 
            file_record = db.query(PPCFile).filter_by(user_id=user_id, uuid=uuid).first()

            if file_record:
                db.delete(file_record)
                db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document deleted successfully",
                "uuid": uuid
            }
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete documents: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
