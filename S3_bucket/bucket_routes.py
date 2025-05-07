from fastapi import APIRouter, UploadFile, File, HTTPException , Form,Depends, Request
from S3_bucket.S3_upload import upload_file_to_s3,upload_title_url
from sqlalchemy.orm import Session
from S3_bucket.fetch_document import fetch_document_from_s3, fetch_seo_cluster_file,fetch_ppc_cluster_file
from fastapi.responses import JSONResponse
from fastapi import Body
from typing import Annotated
from utils import verify_jwt_token, check_api_limit
from S3_bucket.utile import convert_into_csvdata, upload_seo_table, upload_ppc_table
from S3_bucket.delete_doc import seo_cluster_delete_document, ppc_cluster_delete_document
from sqlalchemy.orm.attributes import flag_modified
from auth.models import PPCFile, PPCCSV
from auth.auth import get_db
from botocore.exceptions import ClientError
import pandas as pd
import uuid
import io
import json
router = APIRouter()
from pydantic import BaseModel
from datetime import timedelta
from typing import Optional

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




    

    

   



# Pydantic models for update requests
class KeywordUpdate(BaseModel):
    Keyword: Optional[str]
    # Avg_Monthly_Searches: Optional[int]

class PageUpdate(BaseModel):
    Page_Title: Optional[str]
    # Suggested_URL_Structure: Optional[str]


# Edit a keyword by Keyword_id
# @router.patch("/seo-files/{seo_file_id}/keywords/{keyword_id}")
# def edit_keyword(seo_file_id: int, keyword_id: str, keyword_update: KeywordUpdate, db: Session = Depends(get_db)):
#     seo_file = db.query(SEOFile).filter(SEOFile.id == seo_file_id).first()
#     if not seo_file:
#         raise HTTPException(status_code=404, detail="SEO file not found")
#     json_data = seo_file.json_data
#     try:
#         page_title_id, _ = keyword_id.split(".")
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid keyword_id format")
#     for page in json_data:
#         if page["Page_title_id"] == page_title_id:
#             for kw in page["Keywords"]:
#                 if kw["Keyword_id"] == keyword_id:
#                     if keyword_update.Keyword is not None:
#                         kw["Keyword"] = keyword_update.Keyword
#                     # if keyword_update.Avg_Monthly_Searches is not None:
#                     #     kw["Avg_Monthly_Searches"] = keyword_update.Avg_Monthly_Searches
#                     seo_file.json_data = json_data
#                     db.commit()
#                     return {"message": "Keyword updated"}
#             raise HTTPException(status_code=404, detail="Keyword not found")
#     raise HTTPException(status_code=404, detail="Page not found")

# Delete a page by Page_title_id




from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel

class HeadlineUpdate(BaseModel):
    Headlines_id: Optional[str] = None
    Ad_Headline: str


class DescriptionUpdate(BaseModel):
    Description_id: Optional[str] = None
    Description: str


# class KeywordUpdate(BaseModel):
#     Keyword_id: Optional[str] = None
#     Keyword: str
#     Avg_Monthly_Searches: Optional[int] = None

class ppcPageUpdate(BaseModel):
    # Page_Title: Optional[str] = None
    Ad_Group: Optional[str] = None
    Ad_Headlines: Optional[List[Union[HeadlineUpdate]]] = None
    Descriptions: Optional[List[Union[DescriptionUpdate]]] = None
    # Keywords: Optional[List[Union[KeywordUpdate, str]]] = None


