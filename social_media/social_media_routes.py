from fastapi import APIRouter, UploadFile, File, HTTPException , Form
from typing import Optional
import pandas as pd
import io
from social_media.Agents.social_media import agent_call
from social_media.Agents.document_summared import Document_summerizer
from S3_bucket.fetch_document import download_document
import json

router = APIRouter()

# Soical media post
@router.post("/social_media_post")
async def social_media_post(file: UploadFile = File(...),json_data: Optional[str] = Form(None)):
    try:
        if not file:
            return {"error": "No file uploaded"}
        
        # Fixed the condition logic - was missing a 'not' and had incorrect operator
        if not file.filename.endswith((".docx", ".doc")):
            return {"error": "Invalid file format. Please upload a Word document (.docx or .doc)"}
        
        dict_data = json.loads(json_data)
        text = download_document(dict_data['data'])
        # print(text)
        json_data = Document_summerizer(text)
 
        file_contents = await file.read()
        # print(json_data)
        # json_data_dict = json.loads(json_data) if json_data else None
        # print(json_data_dict)
        result = agent_call(file=file_contents,json_data=json_data,file_name=file.filename, num_iterations=5)
  
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))