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
from social_media_models import UUIDRequest, PostUpdate
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
    fileName : Optional[str] = Form(None),
    text_data: Optional[str] = Form(None),
    json_data: Optional[str] = Form(None),
    linkedIn_post: Optional[bool] = Form(True),
    facebook_post: Optional[bool] = Form(True),
    twitter_post: Optional[bool] = Form(True),
    hash_tag: Optional[bool] = Form(False),
    emoji: Optional[bool] = Form(False),
    objectives: Optional[str] = Form(None),
    audience : Optional[str] = Form(None),
    user = Depends(check_api_limit("social_media")),
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    try:
        if not file and not text_data:
            raise HTTPException(status_code=400, detail="Either file or text_data must be provided")

        if file and not file.filename.endswith((".docx", ".doc")):
            raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .docx or .doc file")

        summarized_data = {}

        file_contents = await file.read() if file else text_data.encode()
        text = convert_doc_to_text(file_contents, file.filename if file else "uploaded_text")

        loop = asyncio.get_running_loop()
        tasks = []

        if linkedIn_post:
            tasks.append(loop.run_in_executor(None, linkedIn_agent_call, text, summarized_data, 5, hash_tag, emoji))
        if facebook_post:
            tasks.append(loop.run_in_executor(None, facebook_agent_call, text, summarized_data, 5, hash_tag, emoji))
        if twitter_post:
            tasks.append(loop.run_in_executor(None, twitter_agent_call, text, summarized_data, 5, hash_tag, emoji))

        responses = await asyncio.gather(*tasks)
        results = {}
        total_tokens = 0
        index = 0

        if linkedIn_post:
            linkedin_data, linkedin_tokens = responses[index]
            results["linkedin_posts"] = linkedin_data
            total_tokens += linkedin_tokens
            index += 1

        if facebook_post:
            facebook_data, facebook_tokens = responses[index]
            results["facebook_posts"] = facebook_data
            total_tokens += facebook_tokens
            index += 1

        if twitter_post:
            twitter_data, twitter_tokens = responses[index]
            results["twitter_posts"] = twitter_data
            total_tokens += twitter_tokens

        print(results)

        # Update token usage and/or call count
        social_media_record = db.query(SocialMedia).filter(SocialMedia.user_id == user.id).first()
        if social_media_record:
            if total_tokens > 0:
                social_media_record.total_tokens += total_tokens
            if not results:
                social_media_record.call_count = max(social_media_record.call_count - 1, 0)
            db.commit()

        return results

    except ValueError as e:
        traceback.print_exc()
        # Decrement call_count on exception
        social_media_record = db.query(SocialMedia).filter(SocialMedia.user_id == user.id).first()
        if social_media_record:
            social_media_record.call_count = max(social_media_record.call_count - 1, 0)
            db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        traceback.print_exc()
        # Decrement call_count on exception
        social_media_record = db.query(SocialMedia).filter(SocialMedia.user_id == user.id).first()
        if social_media_record:
            social_media_record.call_count = max(social_media_record.call_count - 1, 0)
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/socialmedia_uploaddata")  
async def socialmedia_upload_data(json_data: dict = Body(...),
    id: str = Depends(verify_jwt_token),
    # user = Depends(check_api_limit("social_media"))
    ):
      
    try:
        # Read file content
        file_content = json_data.get("data", [])

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
        
        if len(file_content) != 1 or not isinstance(file_content[0], dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid data format"
            )
        
        data_dict = file_content[0]
        
        linkedin_data = data_dict.get("linkedin_posts", [])
        facebook_data = data_dict.get("facebook_posts", [])
        twitter_data = data_dict.get("twitter_posts", [])

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


@router.delete("/socialmedia_linkedin/{uuid}/post/{LinkedIn_id}")
async def socialmedia_delete_linkedin(
    uuid: str,
    LinkedIn_id: str,
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    user_id = int(id[1])
    seo_file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()

    if not seo_file:
        raise HTTPException(status_code=404, detail="Social media file not found")

    posts = seo_file.linkedIn_post 
    updated_posts = [p for p in posts if p.get("LinkedIn_id") != LinkedIn_id]

    if len(updated_posts) == len(posts):
        raise HTTPException(status_code=404, detail="Post not found")

    seo_file.linkedIn_post = updated_posts
    flag_modified(seo_file, "linkedIn_post")

    try:
        db.commit()
        db.refresh(seo_file)
        return {"message": f"Post with LinkedIn_id {LinkedIn_id} deleted."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes")

@router.delete("/socialmedia_facebook/{uuid}/post/{facebook_id}")
async def Socialmedia_delete_facebook(
    uuid: str,
    facebook_id: str,
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    user_id = int(id[1])
    seo_file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()

    if not seo_file:
        raise HTTPException(status_code=404, detail="Social media file not found")

    posts = seo_file.facebook_post 
    updated_posts = [p for p in posts if p.get("facebook_id") != facebook_id]

    if len(updated_posts) == len(posts):
        raise HTTPException(status_code=404, detail="Post not found")

    seo_file.linkedIn_post = updated_posts
    flag_modified(seo_file, "linkedIn_post")

    try:
        db.commit()
        db.refresh(seo_file)
        return {"message": f"Post with facebook_id {facebook_id} deleted."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes")

@router.delete("/socialmedia_twitter/{uuid}/post/{twitter_id}")
async def Socialmedia_delete_twitter(
    uuid: str,
    twitter_id: str,
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    user_id = int(id[1])
    seo_file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()

    if not seo_file:
        raise HTTPException(status_code=404, detail="Social media file not found")

    posts = seo_file.twitter_post
    updated_posts = [p for p in posts if p.get("twitter_id") != twitter_id]

    if len(updated_posts) == len(posts):
        raise HTTPException(status_code=404, detail="Post not found")

    seo_file.linkedIn_post = updated_posts
    flag_modified(seo_file, "linkedIn_post")

    try:
        db.commit()
        db.refresh(seo_file)
        return {"message": f"Post with twitter_id {twitter_id} deleted."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes")

@router.patch("/socialmedia_linkedin/{uuid}/post/{LinkedIn_id}")
async def socialmedia_edit_linkedin(
    uuid: str, 
    LinkedIn_id: str,
    page_update: PostUpdate,
    db: Session = Depends(get_db), 
    id: str = Depends(verify_jwt_token)):

    user_id = int(id[1])
    
    file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
    if not file:
        raise HTTPException(status_code=404, detail="LinkedIn file not found")
    
    json_data = file.linkedIn_post

    if not json_data:
        raise HTTPException(status_code=404, detail="No LinkedIn posts found")

    found = False
    for page in json_data:
        if page.get("linkedIn_id") == LinkedIn_id:
            if page_update.content is not None:
                page["LinkedIn"] = page_update.content
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="post not found")

    file.linkedIn_post = json_data
    flag_modified(file, "linkedIn_post")

    try:
        db.commit()
        db.refresh(file)
        return {"message": "Page updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")

@router.patch("/socialmedia_facebook/{uuid}/post/{Facebook_id}")
async def socialmedia_edit_facebook(
    uuid: str, 
    Facebook_id: str,
    page_update: PostUpdate,
    db: Session = Depends(get_db), 
    id: str = Depends(verify_jwt_token)):

    user_id = int(id[1])
    
    file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
    if not file:
        raise HTTPException(status_code=404, detail="facebook file not found")
    
    json_data = file.facebook_post

    if not json_data:
        raise HTTPException(status_code=404, detail="No facebook posts found")

    found = False
    for page in json_data:
        if page.get("Facebook_id") == Facebook_id:
            if page_update.content is not None:
                page["Facebook"] = page_update.content
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="post not found")

    file.facebook_post = json_data
    flag_modified(file, "Facebook_post")

    try:
        db.commit()
        db.refresh(file)
        return {"message": "post updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")
    
@router.patch("/socialmedia_twitter/{uuid}/post/{Twitter_id}")
async def socialmedia_edit_twitter(
    uuid: str, 
    Twitter_id: str,
    page_update: PostUpdate,
    db: Session = Depends(get_db), 
    id: str = Depends(verify_jwt_token)):

    user_id = int(id[1])
    
    file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
    if not file:
        raise HTTPException(status_code=404, detail="twitter file not found")
    
    json_data = file.twitter_post

    if not json_data:
        raise HTTPException(status_code=404, detail="No twitter posts found")

    found = False
    for page in json_data:
        if page.get("Twitter_id") == Twitter_id:
            if page_update.content is not None:
                page["Twitter"] = page_update.content
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="post not found")

    file.twitter_post = json_data
    flag_modified(file, "Facebook_post")

    try:
        db.commit()
        db.refresh(file)
        return {"message": "post updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")    
    
