from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Form
from typing import Optional
import pandas as pd
import io
import uuid
from social_media.Agents.social_media import agent_call
from social_media.Agents.document_summared import Document_summerizer
from social_media.Agents.linkedin_post import linkedIn_agent_call
from social_media.Agents.facebook_post import facebook_agent_call
from social_media.Agents.twitter_post import twitter_agent_call
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
    

# @router.post("/seo_cluster_uploadfile")  
# async def csv_seo_upload_file(json_data: dict = Body(...),
#     id: str = Depends(verify_jwt_token),
#     user=Depends(check_api_limit("social_media"))):
      
#     try:
        
#         # Read file content
#         file_content = json_data.get("data", [])

#         if not file_content:
#             raise HTTPException(
#                 status_code=400,
#                 detail="No data provided"
#             )
        
#         # data = convert_into_csvdata(file_content)
#         # df = pd.DataFrame(data)
#         # print(df.head())
#         json_str = json.dumps(file_content)

#         # Create a buffer for the JSON data
#         json_buffer = io.StringIO(json_str)
#         json_buffer.seek(0)

#         # csv_buffer = io.StringIO()
#         # df.to_csv(csv_buffer, index=False)
#         # csv_buffer.seek(0)  # Go to start of buffer

#         unique_id = uuid.uuid4().hex
        
#         max_size = 10 * 1024 * 1024  
#         if json_buffer.tell() > max_size:
#             raise HTTPException(
#                 status_code=400,
#                 detail="File size exceeds maximum limit of 10MB"
#             )

   
#         filename = json_data.get("fileName", None)

#         if not filename:
#             raise HTTPException(
#                 status_code=400,
#                 detail="No filename provided"
#             )

     
#         your_tuple = id
#         user_id = your_tuple[1] 
#         user_folder = f"User_{user_id}"
#         # print(user_folder)
#         # print(user_id)
#         folder_name = "seo_clustering_data"

#         s3_path = upload_title_url(user_folder, json_buffer.getvalue(), str(unique_id), folder_name)

#         if s3_path is None:
#             raise HTTPException(
#                 status_code=500,
#                 detail="Failed to upload file to S3"
#             )
        
#         if s3_path:
#             upload_seo_table(str(unique_id), user_id, filename, file_content )

#         return JSONResponse(
#             status_code=200,
#             content={
#                 "message": "File uploaded successfully",
#                 "s3_path": s3_path,
#                 "filename": filename,
#                 "category": folder_name
#             }
#         )

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"An unexpected error occurred: {str(e)}"
#         )    