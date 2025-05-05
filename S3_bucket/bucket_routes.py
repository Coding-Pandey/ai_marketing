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
from auth.models import SEOFile, SEOCSV, PPCFile, PPCCSV
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

@router.get("/seo_Clusterfiles_list")
async def seo_csv_documents(db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    try:
        user_id = int(id[1])  # Extract user_id from the JWT token
        seo_files = db.query(SEOFile).filter(SEOFile.user_id == user_id).all()
        if not seo_files:
            return []
        
        file_count = len(seo_files)


        # Fetch the SEOCSV record for last_reset value
        seo_csv_record = db.query(SEOCSV).filter(SEOCSV.user_id == user_id).first()

        if seo_csv_record:
        
            seo_csv_record.file_count = file_count
            seo_csv_record.call_count = file_count
            db.commit()

        # Include last_reset in each file entry
        result = [
            {
                "file_name": seo_file.file_name,
                "uuid": seo_file.uuid,
                "last_reset": seo_file.upload_time + timedelta(days=30) if seo_file.upload_time else None,
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
        if not ppc_files:
            return []
        
        file_count = len(ppc_files)

        ppc_csv_record = db.query(PPCCSV).filter(PPCCSV.user_id == user_id).first()


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
                "last_reset": ppc_file.upload_time + timedelta(days=30) if ppc_file.upload_time else None,
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
            upload_seo_table(str(unique_id), user_id, filename, file_content )

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
            upload_ppc_table(str(unique_id), user_id, filename, file_content)

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
    
@router.get("/seo_cluster_fetch_data/{uuid}")
async def seo_fetch_document(uuid: str, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    
    try:
        if uuid is None:
            raise HTTPException(status_code=200, detail="UUID is required")
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = str(uuid)  # Ensure uuid is a string
        seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=uuid).first()
     
        # print(f"json_data: {seo_file.json_data}")
        if not seo_file:
            raise HTTPException(status_code=200, detail="File not found for this user")
        
        data = fetch_seo_cluster_file(user_id, uuid)
        if not data:
            raise HTTPException(status_code=200, detail="No documents found for the user")
        
        json_data = json.loads(data["documents"])
        

        json_data = {
            "id": uuid,
            "fileName": seo_file.file_name,
            "data": seo_file.json_data
        }
        return json_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/ppc_cluster_fetch_data/{uuid}")
async def ppc_fetch_document(uuid: str, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        if uuid is None:
            raise HTTPException(status_code=200, detail="UUID is required")
        user_id = str(id[1]) 
        uuid = str(uuid) 
        ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=uuid).first()
        if not ppc_file:
            raise HTTPException(status_code=200, detail="File not found for this user")
        data = fetch_ppc_cluster_file(user_id, uuid)
        if not data:
            raise HTTPException(status_code=200, detail="No documents found for the user")
        json_data = json.loads(data["documents"])

        json_data = {
            "id": uuid,
            "fileName": ppc_file.file_name,
            "data": ppc_file.json_data
        }
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
        success = ppc_cluster_delete_document(uuid, user_id)
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


# Pydantic models for update requests
class KeywordUpdate(BaseModel):
    Keyword: Optional[str]
    # Avg_Monthly_Searches: Optional[int]

class PageUpdate(BaseModel):
    Page_Title: Optional[str]
    # Suggested_URL_Structure: Optional[str]

# Delete a keyword by Keyword_id
@router.delete("/seo-files/{seo_file_uuid}/keywords/{keyword_id}")
def seo_delete_keyword(seo_file_uuid: str, keyword_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])  # Extract user_id from the JWT token
    seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
    # seo_file = db.query(SEOFile).filter(SEOFile.uuid == seo_file_uuid).first()
    if not seo_file:
        raise HTTPException(status_code=404, detail="SEO file not found")
    json_data = seo_file.json_data
    try:
        page_title_id, _ = keyword_id.split(".")
        print(page_title_id)
        print(keyword_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid keyword_id format")
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            keywords = page["Keywords"]
            print(keywords)
            for kw in keywords:
                if kw["Keyword_id"] == keyword_id:
                    keywords.remove(kw)
                    seo_file.json_data = json_data
                    print(seo_file.json_data)
                    flag_modified(seo_file, "json_data")
    
                    try:
                        db.commit()
                        db.refresh(seo_file)  # Refresh to confirm database state

                        return {"message": "Keyword deleted"}
                    except Exception as e:
    
                        db.rollback()
                        raise HTTPException(status_code=500, detail="Failed to save changes")
                    # return {"message": "Keyword deleted"}
            raise HTTPException(status_code=404, detail="Keyword not found")
    raise HTTPException(status_code=404, detail="Page not found")

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
@router.delete("/seo-files/{seo_file_uuid}/pages/{page_title_id}")
def seo_delete_page(seo_file_uuid: str, page_title_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])
    seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
    if not seo_file:
        raise HTTPException(status_code=404, detail="SEO file not found")
    json_data = seo_file.json_data
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            json_data.remove(page)
            seo_file.json_data = json_data
            flag_modified(seo_file, "json_data")
            try:
                db.commit()
                db.refresh(seo_file) 
                return {"message": "Page deleted"} # Refresh to confirm database state
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to save changes")
    raise HTTPException(status_code=404, detail="Page not found")

# Edit a page by Page_title_id
@router.patch("/seo-files/{seo_file_uuid}/pages/{page_title_id}")
def seo_edit_page(seo_file_uuid: str, page_title_id: str, page_update: PageUpdate, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):

    user_id = int(id[1])
    
    # Extract user_id from the JWT token    
    # seo_file = db.query(SEOFile).filter(SEOFile.uuid == seo_file_uuid).first()
    seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
    if not seo_file:
        raise HTTPException(status_code=404, detail="SEO file not found")
    json_data = seo_file.json_data
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            if page_update.Page_Title is not None:
                page["Page_Title"] = page_update.Page_Title
            # if page_update.Suggested_URL_Structure is not None:
            #     page["Suggested_URL_Structure"] = page_update.Suggested_URL_Structure
            seo_file.json_data = json_data
            flag_modified(seo_file, "json_data")
            try:
                db.commit()
                db.refresh(seo_file)  # Refresh to confirm database state
                return {"message": "Page updated"}
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to save changes")
          
    raise HTTPException(status_code=404, detail="Page not found")



@router.delete("/ppc-files/{ppc_file_uuid}/keywords/{keyword_id}")
def ppc_delete_keyword(ppc_file_uuid: str, keyword_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])  # Extract user_id from the JWT token
    ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=ppc_file_uuid).first()
    if not ppc_file:
        raise HTTPException(status_code=404, detail="PPC file not found")
    json_data = ppc_file.json_data
    try:
        page_title_id, _ = keyword_id.split(".")
        print(page_title_id)
        print(keyword_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid keyword_id format")
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            keywords = page["Keywords"]
            print(keywords)
            for kw in keywords:
                if kw["Keyword_id"] == keyword_id:
                    keywords.remove(kw)
                    ppc_file.json_data = json_data
                    # print(ppc_file.json_data)
                    flag_modified(ppc_file, "json_data")
    
                    try:
                        db.commit()
                        db.refresh(ppc_file)  # Refresh to confirm database state

                        return {"message": "Keyword deleted"}
                    except Exception as e:
    
                        db.rollback()
                        raise HTTPException(status_code=500, detail="Failed to save changes")
                    # return {"message": "Keyword deleted"}
            raise HTTPException(status_code=404, detail="Keyword not found")
    raise HTTPException(status_code=404, detail="Page not found")


@router.delete("/ppc-files/{ppc_file_uuid}/pages/{page_title_id}")
def ppc_delete_page(ppc_file_uuid: str, page_title_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])
    ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=ppc_file_uuid).first()
    if not ppc_file:
        raise HTTPException(status_code=404, detail="PPC file not found")
    json_data = ppc_file.json_data
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            json_data.remove(page)
            ppc_file.json_data = json_data
            flag_modified(ppc_file, "json_data")
            try:
                db.commit()
                db.refresh(ppc_file) 
                return {"message": "Page deleted"} 
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to save changes")
    raise HTTPException(status_code=404, detail="Page not found")

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


@router.patch("/ppc-files/{ppc_file_uuid}/pages/{page_title_id}")
def ppc_edit_page(ppc_file_uuid: str, page_title_id: str, page_update: ppcPageUpdate, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):

    user_id = int(id[1])
    # Extract user_id from the JWT token    
    ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=ppc_file_uuid).first()
    if not ppc_file:
        raise HTTPException(status_code=404, detail="PPC file not found")
    
    json_data = ppc_file.json_data
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            # Update Page_Title if provided
            # if page_update.Page_Title is not None:
            #     page["Page_Title"] = page_update.Page_Title
            
            # Update Ad_Group if provided
            if page_update.Ad_Group is not None:
                page["Ad_Group"] = page_update.Ad_Group
            
            # Update Ad_Headlines if provided
            if page_update.Ad_Headlines is not None:
                # Replace or update specific headlines
                if isinstance(page_update.Ad_Headlines, list):
                    updated_headlines = []
                    for i, headline in enumerate(page_update.Ad_Headlines):
                        if isinstance(headline, dict) and "Ad_Headline" in headline:
                            # Create headline with ID if it doesn't exist
                            headline_id = headline.get("Headlines_id", f"{page_title_id}.{i+1}")
                            updated_headlines.append({
                                "Headlines_id": headline_id,
                                "Ad_Headline": headline["Ad_Headline"]
                            })
                        elif isinstance(headline, str):
                            # Simple string headline, create with ID
                            updated_headlines.append({
                                "Headlines_id": f"{page_title_id}.{i+1}",
                                "Ad_Headline": headline
                            })
                    page["Ad_Headlines"] = updated_headlines
            
            # Update Descriptions if provided
            if page_update.Descriptions is not None:
                # Replace or update specific descriptions
                if isinstance(page_update.Descriptions, list):
                    updated_descriptions = []
                    for i, description in enumerate(page_update.Descriptions):
                        if isinstance(description, dict) and "Description" in description:
                            # Create description with ID if it doesn't exist
                            description_id = description.get("Description_id", f"{page_title_id}.{i+1}")
                            updated_descriptions.append({
                                "Description_id": description_id,
                                "Description": description["Description"]
                            })
                        elif isinstance(description, str):
                            # Simple string description, create with ID
                            updated_descriptions.append({
                                "Description_id": f"{page_title_id}.{i+1}",
                                "Description": description
                            })
                    page["Descriptions"] = updated_descriptions
            
            # Update Keywords if provided
            if page_update.Keywords is not None:
                # Handle keyword updates
                if isinstance(page_update.Keywords, list):
                    updated_keywords = []
                    for i, keyword in enumerate(page_update.Keywords):
                        if isinstance(keyword, dict) and "Keyword" in keyword:
                            # Create keyword with ID if it doesn't exist
                            keyword_id = keyword.get("Keyword_id", f"{page_title_id}.{i+1}")
                            keyword_data = {
                                "Keyword_id": keyword_id,
                                "Keyword": keyword["Keyword"]
                            }
                            # Include search volume if provided
                            if "Avg_Monthly_Searches" in keyword:
                                keyword_data["Avg_Monthly_Searches"] = keyword["Avg_Monthly_Searches"]
                            updated_keywords.append(keyword_data)
                        elif isinstance(keyword, str):
                            # Simple string keyword, create with ID
                            updated_keywords.append({
                                "Keyword_id": f"{page_title_id}.{i+1}",
                                "Keyword": keyword,
                                "Avg_Monthly_Searches": 0  # Default value, could be updated from a service
                            })
                    page["Keywords"] = updated_keywords
            
            # Save changes to database
            ppc_file.json_data = json_data
            flag_modified(ppc_file, "json_data")
            try:
                db.commit()
                db.refresh(ppc_file)  # Refresh to confirm database state
                return {"message": "Page updated successfully"}
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")
          
    raise HTTPException(status_code=404, detail="Page not found")