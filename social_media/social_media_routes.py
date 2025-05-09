from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Form
from typing import Optional
import pandas as pd
import io
import uuid
from datetime import timedelta
from sqlalchemy.orm import Session
from social_media.Agents.social_media import agent_call
from social_media.Agents.document_summared import Document_summerizer
from social_media.Agents.linkedin_post import linkedIn_agent_call
from social_media.Agents.facebook_post import facebook_agent_call
from social_media.Agents.twitter_post import twitter_agent_call
from social_media.utils import upload_socialmedia_table
from social_media_models import UUIDRequest
from S3_bucket.fetch_document import download_document
from fastapi.responses import JSONResponse
import json
import asyncio
from social_media.utils import convert_doc_to_text
router = APIRouter()
import traceback
from utils import verify_jwt_token, check_api_limit
from sqlalchemy.orm.attributes import flag_modified
from auth.auth import get_db
from auth.models import SocialMediaFile, SocialMedia
# Soical media post
@router.post("/social_media_post")
async def social_media_post(
    file: Optional[UploadFile] = File(None),
    text_data: Optional[str] = Form(None),
    json_data: Optional[str] = Form(None),
    linkedIn_post: Optional[bool] = Form(True),
    facebook_post: Optional[bool] = Form(True),
    twitter_post: Optional[bool] = Form(True),
    hash_tag: Optional[bool] = Form(False),
    emoji: Optional[bool] = Form(False)
):
    try:
        if not file and not text_data:
            raise HTTPException(status_code=400, detail="Either file or text_data must be provided")

        if file and not file.filename.endswith((".docx", ".doc")):
            raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .docx or .doc file")
        
    
        # dict_data = json.loads(json_data) if json_data else {}
        # text = download_document(dict_data.get("data", ""))
        # summarized_data = Document_summerizer(text)
        summarized_data = {}

        file_contents = await file.read() if file else text_data.encode()

        text = convert_doc_to_text(file_contents,file.filename)
        tasks = []
        results = {}

        # if linkedIn_post:
        #     tasks.append(linkedIn_agent_call(text=text, json_data=summarized_data, num_iterations=5, hash_tag=hash_tag, emoji=emoji))
        # if facebook_post:
        #     tasks.append(facebook_agent_call(text=text, json_data=summarized_data, num_iterations=5, hash_tag=hash_tag, emoji=emoji))
        # if twitter_post:
        #     tasks.append(twitter_agent_call(text= text, json_data=summarized_data, num_iterations=5, hash_tag=hash_tag, emoji=emoji))

        # responses = await asyncio.gather(*tasks)
        loop = asyncio.get_running_loop()

        # Add tasks using run_in_executor
        if linkedIn_post:
            tasks.append(loop.run_in_executor(None, linkedIn_agent_call, text, summarized_data, 5, hash_tag, emoji))
        if facebook_post:
            tasks.append(loop.run_in_executor(None, facebook_agent_call, text, summarized_data, 5, hash_tag, emoji))
        if twitter_post:
            tasks.append(loop.run_in_executor(None, twitter_agent_call, text, summarized_data, 5, hash_tag, emoji))

        # Run tasks concurrently and await results
        responses = await asyncio.gather(*tasks)

        # Map results back based on order of execution
        index = 0
        if linkedIn_post:
            results["linkedin_posts"] = responses[index]
            index += 1
        if facebook_post:
            results["facebook_posts"] = responses[index]
            index += 1
        if twitter_post:
            results["twitter_posts"] = responses[index]

        print(results)    

        return results
  
    except ValueError as e:
        traceback.print_exc() 
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/socialmedia_uploaddata")  
async def socialmedia_upload_data(json_data: dict = Body(...),
                              
    id: str = Depends(verify_jwt_token),
    user=Depends(check_api_limit("social_media"))):
      
    try:
        
        # Read file content
        file_content = json_data.get("data", [])

        linkedin_data = file_content.get("linkedin", [])
        facebook_data = file_content.get("facebook", [])
        twitter_data = file_content.get("twitter", [])

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
        
        unique_id = uuid.uuid4().hex 
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
        folder_name = "socialmedia_data"

        result = upload_socialmedia_table(str(unique_id), user_id, filename, linkedIn=linkedin_data,facebook_post=facebook_data,twitter_post=twitter_data)

        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "database": result,
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
    

@router.get("/socialmedia_datalist")
async def socialmedia_documents(db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):

    try:
        user_id = int(id[1])  
        socialmedia_files = db.query(SocialMediaFile).filter(SocialMediaFile.user_id == user_id).all()
        if not socialmedia_files:
            return []
        
        file_count = len(socialmedia_files)


        socialmedia_record = db.query(SocialMedia).filter(SocialMedia.user_id == user_id).first()

        if socialmedia_record:
        
            socialmedia_record.file_count = file_count
            socialmedia_record.call_count = file_count
            db.commit()

   
        result = [
            {
                "file_name": socialmedia_file.file_name,
                "uuid": socialmedia_file.uuid,
                "last_reset": socialmedia_file.upload_time + timedelta(days=30) if socialmedia_file.upload_time else None,
            }
            for socialmedia_file in socialmedia_files
        ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    

@router.delete("/socialmedia_delete_document")
async def socialmedia_delete_document(request: UUIDRequest, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = request.uuid
        # success = seo_cluster_delete_document(uuid, user_id)
        # if success:
            # 2. Delete DB record
        user_id = int(id[1]) 
        file_record = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()

        if file_record:
            db.delete(file_record)
            db.commit()
            db.refresh() 

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document deleted successfully",
                "uuid": uuid
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   
    except Exception as e:
        db.rollback()
        raise Exception(f"Error storing SEO file in table: {str(e)}")
    finally:
        db.close()  


# @router.delete("/seo-files/{seo_file_uuid}/keywords/{keyword_id}")
# async def seo_delete_keyword(seo_file_uuid: str, keyword_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
#     user_id = int(id[1])  # Extract user_id from the JWT token
#     seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
#     # seo_file = db.query(SEOFile).filter(SEOFile.uuid == seo_file_uuid).first()
#     if not seo_file:
#         raise HTTPException(status_code=404, detail="SEO file not found")
#     json_data = seo_file.json_data
#     try:
#         page_title_id, _ = keyword_id.split(".")
#         print(page_title_id)
#         print(keyword_id)
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid keyword_id format")
#     for page in json_data:
#         if page["Page_title_id"] == page_title_id:
#             keywords = page["Keywords"]
#             print(keywords)
#             for kw in keywords:
#                 if kw["Keyword_id"] == keyword_id:
#                     keywords.remove(kw)
#                     seo_file.json_data = json_data
#                     print(seo_file.json_data)
#                     flag_modified(seo_file, "json_data")
    
#                     try:
#                         db.commit()
#                         db.refresh(seo_file)  # Refresh to confirm database state

#                         return {"message": "Keyword deleted"}
#                     except Exception as e:
    
#                         db.rollback()
#                         raise HTTPException(status_code=500, detail="Failed to save changes")
#                     # return {"message": "Keyword deleted"}
#             raise HTTPException(status_code=404, detail="Keyword not found")
#     raise HTTPException(status_code=404, detail="Page not found")
