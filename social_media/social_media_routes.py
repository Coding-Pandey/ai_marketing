from fastapi import APIRouter, UploadFile, File, HTTPException , Form
from typing import Optional
import pandas as pd
import io
from social_media.Agents.social_media import agent_call
from social_media.Agents.document_summared import Document_summerizer
from social_media.Agents.linkedin_post import linkedIn_agent_call
from social_media.Agents.facebook_post import facebook_agent_call
from social_media.Agents.twitter_post import twitter_agent_call
from S3_bucket.fetch_document import download_document
import json
import asyncio

router = APIRouter()

# Soical media post
@router.post("/social_media_post")
async def social_media_post(
    file: UploadFile = File(...),
    json_data: Optional[str] = Form(None),
    linkedIn_post: Optional[bool] = Form(True),
    facebook_post: Optional[bool] = Form(True),
    twitter_post: Optional[bool] = Form(True),
    hash_tag: Optional[bool] = Form(False),
    emoji: Optional[bool] = Form(False)
):
    try:
        if not file:
            return {"error": "No file uploaded"}

        if not file.filename.endswith((".docx", ".doc")):
            return {"error": "Invalid file format. Please upload a Word document (.docx or .doc)"}

        dict_data = json.loads(json_data) if json_data else {}
        text = download_document(dict_data.get("data", ""))
        summarized_data = Document_summerizer(text)

        file_contents = await file.read()

        tasks = []
        results = {}

        if linkedIn_post:
            tasks.append(linkedIn_agent_call(file=file_contents, file_name=file.filename, json_data=summarized_data, num_iterations=5, hash_tag=hash_tag, emoji=emoji))
        if facebook_post:
            tasks.append(facebook_agent_call(file=file_contents, file_name=file.filename, json_data=summarized_data, num_iterations=5, hash_tag=hash_tag, emoji=emoji))
        if twitter_post:
            tasks.append(twitter_agent_call(file=file_contents, file_name=file.filename, json_data=summarized_data, num_iterations=5, hash_tag=hash_tag, emoji=emoji))

        responses = await asyncio.gather(*tasks)

        # Map results back based on order of execution
        index = 0
        if linkedIn_post:
            results["linkedin"] = responses[index]
            index += 1
        if facebook_post:
            results["facebook"] = responses[index]
            index += 1
        if twitter_post:
            results["twitter"] = responses[index]

        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))