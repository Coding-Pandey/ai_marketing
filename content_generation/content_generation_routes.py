from fastapi import APIRouter, UploadFile, File, HTTPException , Form
from typing import Optional
from social_media.Agents.document_summared import Document_summerizer
from S3_bucket.fetch_document import download_document
from S3_bucket.fetch_document import download_document, download_csv
from content_generation.blog_agent.blog_generation import blog_generation
from content_generation.blog_agent.seo_blog import generation_blog_async
import json

router = APIRouter()

@router.post("/blog_generation")
async def Blog_generation(file: UploadFile = File(...), json_data: Optional[str] = Form(None) ):
    try:
        dict_data = json.loads(json_data)
        # print(dict_data)
        text = download_document(dict_data['data'])

        if all(isinstance(v, list) and not v for v in text.values()):
            print("All folders are empty lists. Skipping summarization.")
            summerized_text_json, doc_token = {}, 0
        else:
            summerized_text_json, doc_token = Document_summerizer(text)
       
        json_data, blogg_token = blog_generation(file= file, json_data=summerized_text_json)
        
        print(f"Document summerized token: {doc_token}, blog token: {blogg_token}")
        total_token = doc_token + blogg_token
        print({f"Total token: {total_token}"})
        return json_data, total_token
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   


@router.post("/seo_based_blog")
async def Seo_based_blog(csv_data: str = Form(...), text: Optional[str] = Form(None)):
    try:
        parsed_data = json.loads(csv_data) 
        # print(parsed_data)
        json_data = download_csv(parsed_data['data'])
        # print(json_data)
        keywords = [item['keyword'] for item in json_data['csv']]
        new_blog ,total_tokens_used = await generation_blog_async(keywords, text)
        print(f"total Seo blog {total_tokens_used}")
        return new_blog, total_tokens_used

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    

