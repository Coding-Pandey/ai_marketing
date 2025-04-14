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
        # print(text)
        summerized_text_json = Document_summerizer(text)
       
        json_data = blog_generation(file= file, json_data=summerized_text_json)
        print(json_data)
   
        return json_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   


@router.post("/seo_based_blog")
async def Seo_based_blog(csv_data: str = Form(...), text: Optional[str] = Form(None)):
    try:
        parsed_data = json.loads(csv_data) 
        print(parsed_data)
        json_data = download_csv(parsed_data['data'])
        print(json_data)
        keywords = [item['keyword'] for item in json_data['csv']]
        new_blog = await generation_blog_async(keywords, text)
        
        return new_blog

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    

