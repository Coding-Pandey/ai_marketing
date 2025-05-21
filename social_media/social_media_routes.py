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
from S3_bucket.S3_upload import upload_image_to_s3, generate_presigned_url
from fastapi.responses import JSONResponse
import json
import asyncio
from social_media.utils import convert_doc_to_text
router = APIRouter()
import traceback
from utils import verify_jwt_token, check_api_limit
from sqlalchemy.orm.attributes import flag_modified
from auth.auth import get_db
from auth.models import SocialMediaFile, SocialMedia, LinkedinPost, FacebookPost, TwitterPost
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
        
        # results["tiktok_posts"] = [{}]
        # results["instagram_posts"]  = [{}]
        print(results)

        # Update token usage and/or call count
        social_media_record = db.query(SocialMedia).filter(SocialMedia.user_id == user.id).first()
        if social_media_record:
            if total_tokens > 0:
                social_media_record.total_tokens += total_tokens
            if not results:
                social_media_record.call_count = max(social_media_record.call_count - 1, 0)
            db.commit()
        if results:
            your_tuple = id
            user_id = your_tuple[1] 
            linkedin_file = results.get("linkedin_posts", [])
            facebook_file = results.get("facebook_posts", [])
            twitter_file = results.get("twitter_posts", [])
            unique_id = uuid.uuid4().hex
            result = upload_socialmedia_table(str(unique_id), user_id, fileName, linkedIn=linkedin_file, facebook_post=facebook_file, twitter_post=twitter_file)

        return {"uuid":unique_id,
                "fileName": fileName,
                "data":results}
    

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
                "last_reset": socialmedia_file.last_reset + timedelta(days=30) if socialmedia_file.last_reset else None,
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
            # db.refresh(file_record) 

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
        raise Exception(f"Error storing file in table: {str(e)}")
    finally:
        db.close()  

@router.get("/socialmedia_post_data/{uuid}")
async def socialmedia_fetch_posts(uuid: str, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    
    try:
        if uuid is None:
            raise HTTPException(status_code=200, detail="UUID is required")
        user_id = str(id[1]) 
        print(user_id) # Extract user_id from the JWT token
        uuid = str(uuid)  # Ensure uuid is a string
        file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
     
        # print(f"json_data: {seo_file.json_data}")
        if not file:
            raise HTTPException(status_code=200, detail="File not found for this user")
        
        # data = fetch_seo_cluster_file(user_id, uuid)
        # if not data:
        #     raise HTTPException(status_code=200, detail="No documents found for the user")
        
        # json_data = json.loads(data["documents"])
        

        json_data = {
            "id": uuid,
            "fileName": file.file_name,
            "data": {
                "linkedin_posts": file.linkedIn_post,
                "facebook_posts": file.facebook_post,
                "twitter_posts": file.twitter_post,
            }
        }
        return json_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    updated_posts = [p for p in posts if p.get("linkedin_id") != LinkedIn_id]

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
    
    finally:
        db.close()

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

    seo_file.facebook_post = updated_posts
    flag_modified(seo_file, "facebook_post")

    try:
        db.commit()
        db.refresh(seo_file)
        return {"message": f"Post with facebook_id {facebook_id} deleted."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes")
    finally:
        db.close()

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

    seo_file.twitter_post = updated_posts
    flag_modified(seo_file, "twitter_post")

    try:
        db.commit()
        db.refresh(seo_file)
        return {"message": f"Post with twitter_id {twitter_id} deleted."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes")
    finally:
        db.close()

@router.patch("/socialmedia_linkedin/{uuid}/post/{LinkedIn_id}")
async def socialmedia_edit_linkedin(
    uuid: str,
    LinkedIn_id: str,
    content: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    user_id = int(id[1])
    print(user_id)
    file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
    if not file:
        raise HTTPException(status_code=404, detail="LinkedIn file not found")

    json_data = file.linkedIn_post
    if not json_data:
        raise HTTPException(status_code=404, detail="No LinkedIn posts found")
    
    content = json.loads(content) if content else None
    found = False
    image_url = None  # Initialize image_url to None
    for page in json_data:
        if page.get("linkedin_id") == LinkedIn_id:
            if content is not None:
                page["discription"] = content

            if image is not None:
                file_path = f"User_{user_id}/Socialmedia_data/{uuid}/linkedin_post/{LinkedIn_id}"
                image_url = upload_image_to_s3(image,file_path)
                # image_url = generate_presigned_url(file_path)
                page["image"] = image_url
                print(image_url)


            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="post not found")

    file.linkedIn_post = json_data
    flag_modified(file, "linkedIn_post")


    try:
        db.commit()
        db.refresh(file)
        if image_url:
            return {"image": image_url}
        return {"message": "post updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")

@router.patch("/socialmedia_facebook/{uuid}/post/{Facebook_id}")
async def socialmedia_edit_facebook(
            uuid: str,
            Facebook_id: str,
            content: str = Form(None),
            image: UploadFile = File(None),
            db: Session = Depends(get_db),
            id: str = Depends(verify_jwt_token)
        ):

    user_id = int(id[1])
    print(user_id)
    file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
    if not file:
        raise HTTPException(status_code=404, detail="Facebook file not found")

    json_data = file.facebook_post
    if not json_data:
        raise HTTPException(status_code=404, detail="No Facebook posts found")

    content = json.loads(content) if content else None
    found = False
    image_url = None 
    for page in json_data:
        if page.get("facebook_id") == Facebook_id:
            if content is not None:
                page["discription"] = content

            if image is not None:
                file_path = f"User_{user_id}/Socialmedia_data/{uuid}/facebook_post/{Facebook_id}"
                image_url = upload_image_to_s3(image,file_path)
                # image_url = generate_presigned_url(file_path)
                page["image"] = image_url
                print(image_url)


            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="post not found")

    file.facebook_post = json_data
    flag_modified(file, "facebook_post")

    try:
        db.commit()
        db.refresh(file)
        if image_url:
            return {"image": image_url}
        return {"message": "post updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")
    
@router.patch("/socialmedia_twitter/{uuid}/post/{Twitter_id}")
async def socialmedia_edit_twitter(
    uuid: str,
    Twitter_id: str,
    content: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):

    user_id = int(id[1])
    print(user_id)
    file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
    if not file:
        raise HTTPException(status_code=404, detail="Twitter file not found")

    json_data = file.twitter_post
    if not json_data:
        raise HTTPException(status_code=404, detail="No Twitter posts found")

    content = json.loads(content) if content else None
    found = False
    image_url = None  # Initialize image_url to None
    for page in json_data:
        if page.get("twitter_id") == Twitter_id:
            if content is not None:
                page["discription"] = content

            if image is not None:
                file_path = f"User_{user_id}/Socialmedia_data/{uuid}/twitter_post/{Twitter_id}"
                image_url = upload_image_to_s3(image,file_path)
                # image_url = generate_presigned_url(file_path)
                page["image"] = image_url
                print(image_url)


            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="post not found")

    file.twitter_post = json_data
    flag_modified(file, "twitter_post")

    # if image and content is None:
    #     return {
    #         "twitter_image": image_url
    #     }

    try:
        db.commit()
        db.refresh(file)
        if image_url:
            return {"image": image_url}
        return {"message": "post updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")    
    
@router.post("/schedule_socialmedia_post")
async def schedule_socialmedia_post(
    post_data: PostUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(verify_jwt_token)
):
    try:
        if not post_data.uuid:
            raise HTTPException(status_code=400, detail="UUID is required")
        
        user_id = int(user_id[1])  # Extract user_id from the JWT token

        file = db.query(SocialMediaFile).filter_by(uuid=post_data.uuid, user_id=user_id).first()
        if not file:    
            raise HTTPException(status_code=404, detail="Social media file not found")
        
        
    
        content = post_data.content[0]
        if not content:
            raise HTTPException(status_code=400, detail="Content is required for scheduling")
        if not post_data.schedule_time:
            raise HTTPException(status_code=400, detail="Schedule time is required")
        unique_id = uuid.uuid4().hex
        scheduled_posts = []
        
        if linkedin_id := content.get("linkedin_id"):
            linkedin_post = LinkedinPost(
                file_id = file.id,
                user_id=user_id,
                schedule_time=post_data.schedule_time,
                content=content,
                post_id=linkedin_id,
                copy_uuid=unique_id
            )
            db.add(linkedin_post)
            scheduled_posts.append("LinkedIn")
        
        if facebook_id := content.get("facebook_id"):
            facebook_post = FacebookPost(
                file_id = file.id,
                user_id=user_id,
                schedule_time=post_data.schedule_time,
                content=content,
                post_id=facebook_id,
                copy_uuid=unique_id
            )
            db.add(facebook_post)
            scheduled_posts.append("Facebook")
        
        if twitter_id := content.get("twitter_id"):
            twitter_post = TwitterPost(
                file_id = file.id,
                user_id=user_id,
                schedule_time=post_data.schedule_time,
                content=content,
                post_id=twitter_id,
                copy_uuid=unique_id
            )
            db.add(twitter_post)
            scheduled_posts.append("Twitter")
        
        if not scheduled_posts:
            raise HTTPException(status_code=400, detail="No social media IDs provided")
        
        if linkedin_id:
            found = False
            for post in file.linkedIn_post or []:
                if post.get("linkedin_id") == linkedin_id:
                    post["isSchedule"] = True
                    found = True
                    break
            if not found:
                raise HTTPException(status_code=400, detail=f"LinkedIn post with ID {linkedin_id} not found")
            flag_modified(file, "linkedIn_post")  # Explicitly mark as modified
        
        if facebook_id:
            found = False
            for post in file.facebook_post or []:
                if post.get("facebook_id") == facebook_id:
                    post["isSchedule"] = True
                    found = True
                    break
            if not found:
                raise HTTPException(status_code=400, detail=f"Facebook post with ID {facebook_id} not found")
            flag_modified(file, "facebook_post")  # Explicitly mark as modified
        
        if twitter_id:
            found = False
            for post in file.twitter_post or []:
                if post.get("twitter_id") == twitter_id:
                    post["isSchedule"] = True
                    found = True
                    break
            if not found:
                raise HTTPException(status_code=400, detail=f"Twitter post with ID {twitter_id} not found")
            flag_modified(file, "twitter_post")  # Explicitly mark as modified
        
        # Commit all changes to the database
        db.commit()
        # db.refresh(file)
        
        return {
            "message": f"Post scheduled successfully for {', '.join(scheduled_posts)}",
            "uuid": unique_id,
            "schedule_time": post_data.schedule_time,
            "status": "scheduled",
            "isScheduled": True,
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to schedule post: {str(e)}")
    
@router.get("/socialmedia_scheduled_posts")
async def get_scheduled_posts(db: Session = Depends(get_db), user_id: int = Depends(verify_jwt_token)):
    user_id = int(user_id[1])  # Extract user_id from the JWT token
    linkedIn_posts = db.query(LinkedinPost).filter_by(user_id=user_id).all()
    facebook_posts = db.query(FacebookPost).filter_by(user_id=user_id).all()
    twitter_posts = db.query(TwitterPost).filter_by(user_id=user_id).all()

    # if not linkedIn_posts and not facebook_posts and not twitter_posts: 
    #     raise HTTPException(status_code=404, detail="No scheduled posts found for this UUID")
    if not linkedIn_posts:
        linkedIn_posts = []
    if not facebook_posts:
        facebook_posts = []
    if not twitter_posts:
        twitter_posts = []

    linkedIn_posts = [{"id": post.id, "content": post.content, "schedule_time": post.schedule_time, "uuid": post.copy_uuid} for post in linkedIn_posts]
    facebook_posts = [{"id": post.id, "content": post.content, "schedule_time": post.schedule_time, "uuid": post.copy_uuid} for post in facebook_posts]
    twitter_posts = [{"id": post.id, "content": post.content, "schedule_time": post.schedule_time, "uuid": post.copy_uuid} for post in twitter_posts]


    return {"linkedin_posts": linkedIn_posts,
            "facebook_posts": facebook_posts,
            "twitter_posts": twitter_posts}

@router.delete("/socialmedia_scheduled_posts/{posts}/{uuid}")
async def delete_scheduled_post(posts: str, uuid: str, db: Session = Depends(get_db), user_id: int = Depends(verify_jwt_token)):
    try:
        # Validate parameters
        if not posts or not uuid:
            raise HTTPException(status_code=400, detail="Invalid parameters provided")

        # Validate platform
        valid_platforms = ["linkedin_posts", "facebook_posts", "twitter_posts"]
        if posts not in valid_platforms:
            raise HTTPException(status_code=400, detail="Invalid social media platform specified")
        user_id = int(user_id[1])  # Extract user_id from the JWT token
        # Query the appropriate post based on platform
        if posts == "linkedin_posts":
            post = db.query(LinkedinPost).filter_by(user_id=user_id, copy_uuid=uuid).first()
        elif posts == "facebook_posts":
            post = db.query(FacebookPost).filter_by(user_id=user_id, copy_uuid=uuid).first()
        elif posts == "twitter_posts":
            post = db.query(TwitterPost).filter_by(user_id=user_id, copy_uuid=uuid).first()

        # Check if post exists
        if not post:
            raise HTTPException(status_code=404, detail="Scheduled post not found")

        # Delete the post
        db.delete(post)
        db.commit()
        return {"message": f"{posts} post deleted successfully", "post_id": post.id}

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete post: {str(e)}")

@router.patch("/update_scheduled_posts/{posts}/{uuid}")
async def update_scheduled_post(
    posts: str,
    uuid: str,
    id: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    reschedule_time: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(verify_jwt_token)
):
    # Validate inputs
    if not posts or not uuid:
        raise HTTPException(status_code=400, detail="Posts and UUID are required")

    if posts not in ["linkedin_posts", "facebook_posts", "twitter_posts"]:
        raise HTTPException(status_code=400, detail="Invalid social media platform specified")

    try:
        user_id = int(user_id[1])  # Assuming JWT token returns user_id as a string with prefix
        print(f"Updating {posts} for user {user_id} with UUID {uuid}")

        # Select model and ID field based on platform
        if posts == "linkedin_posts":
            model = LinkedinPost
            id_field = "linkedin_id"
        elif posts == "facebook_posts":
            model = FacebookPost
            id_field = "facebook_id"
        elif posts == "twitter_posts":
            model = TwitterPost
            id_field = "twitter_id"

        # Query the post
        post = db.query(model).filter_by(user_id=user_id, copy_uuid=uuid).first()
        if not post:
            raise HTTPException(status_code=404, detail=f"{posts.replace('_', ' ').title()} not found")

        # Get current content (JSONB column)
        current_content = post.content or {}
        # print(f"Current content: {current_content}")
        if not current_content:
            raise HTTPException(status_code=404, detail=f"No content found in {posts.replace('_', ' ').title()}")

        # Update content if provided
        if content:
            try:
                print(f"Updating content for {posts} with: {content}")
                # new_content = json.loads(content)
                new_content = content
                # isinstance(content, list)
                # new_content = new_content[0]
                print(f"New content: {new_content}")
                # Ensure the provided ID matches the platform-specific ID in the content
                # if id and new_content.get(id_field) != id:
                #     raise HTTPException(status_code=400, detail=f"Provided ID does not match {id_field} in content")
                # Update the entire content
                print(f"Updating content: {new_content}")
                post.content['discription'] = [new_content]
                # print(f"Updated content: {post.content}")
                # post.content = new_content
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for content")

        # Handle image upload
        image_url = None
        if image:
            # Use id if provided
            image_id = id
            file_path = f"User_{user_id}/schedule_data/{uuid}/{posts.replace('_posts', '_post')}/{image_id}"
            image_url = upload_image_to_s3(image, file_path)
            # Update image URL in content
            post.content["image"] = image_url
            print(f"Image uploaded: {image_url}")

        if reschedule_time:
            try:
                from datetime import datetime
                # Parse the reschedule time
                # post.schedule_time = datetime.strptime(reschedule_time, "%Y-%m-%d %H:%M:%S")
                post.schedule_time = reschedule_time
                print(f"Reschedule time updated: {post.schedule_time}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid reschedule time format. Use 'YYYY-MM-DD HH:MM:SS'.")    

        # Mark content as modified
        flag_modified(post, "content")

        # Commit changes
        db.commit()
        db.refresh(post)
        return {
            "message": "Post updated successfully",
            "image_url": image_url if image_url else None,
            "reschedule_time": post.schedule_time.strftime("%Y-%m-%d %H:%M:%S") if post.schedule_time else None,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")

@router.patch("/edit_file_name/{uuid}")
async def edit_file_name(
    uuid: str,
    new_file_name: str = Form(...),
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    try:
        user_id = int(id[1])  # Extract user_id from the JWT token
        file = db.query(SocialMediaFile).filter_by(user_id=user_id, uuid=uuid).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        file.file_name = new_file_name
        flag_modified(file, "file_name")  # Explicitly mark as modified

        db.commit()
        db.refresh(file)
        return {"message": "File name updated successfully", "new_file_name": file.file_name}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update file name: {str(e)}")
    
