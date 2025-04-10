# from chatbot import PROMPT, query_llm, prompt_keyword_suggestion, query_keyword_suggestion
import pandas as pd
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional
import json
from Seo_process.Agents.Keyword_agent import query_keyword_suggestion,query_keywords_description
from Seo_process.Agents.clusterURL_keyword import seo_main
from Ppc_process.Agents.structure_agent import ppc_main
from Seo_process.prompts.keywords_prompt import prompt_keyword,prompt_keyword_suggestion
from social_media.Agents.social_media import agent_call
from social_media.Agents.document_summared import Document_summerizer
from collections import defaultdict
from google_ads.seo_planner import seo_keywords_main
from google_ads.ppc_process import ppc_keywords_main
from content_generation.blog_agent.blog_generation import blog_generation
from content_generation.blog_agent.seo_blog import generation_blog_async
# from utils import flatten_seo_data , extract_first_json_object
import asyncio
from utils import flatten_seo_data , extract_keywords, filter_keywords_by_searches, flatten_ppc_data, remove_branded_keywords, filter_non_branded_keywords, remove_keywords, add_keywords_to_json
import io
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi.responses import JSONResponse
from typing import Annotated, List
from S3_bucket.S3_upload import upload_file_to_s3,upload_title_url
from S3_bucket.fetch_document import fetch_document_from_s3, download_document, download_csv
from typing import Dict


app = FastAPI(title="AI marketing app",
    description="",
    version="1.0.0"
    )


class KeywordRequest(BaseModel):
    keywords: Optional[str] = None
    description: Optional[str] = None
    exclude_values: Optional[List[int]] = []
    branded_keyword: Optional[List[str]] = []
    location_ids: Optional[List[int]] = None
    language_id: Optional[int] = None
    branded_words: Optional[bool] = None

    def validate(self):
        if not self.keywords and not self.description:
            raise ValueError("At least one of 'keywords' or 'description' must be provided")
        if self.location_ids is None or self.language_id is None:
            raise ValueError("Both 'location_ids' and 'language_id' must be provided")

class SuggestionKeywordRequest(BaseModel):
    keywords: Optional[str] = None
    description: Optional[str] = None

    def validate(self):
        if not self.keywords and not self.description:
            raise ValueError("At least one of 'keywords' or 'description' must be provided") 

# Pydantic model to validate incoming dictionary
class DocumentData(BaseModel):
    data: Dict[str, str]          

class CsvData(BaseModel):
    data: Dict[str, str] 

@app.post("/seo_generate_keywords")
def seo_generate_keywords(request: KeywordRequest):
    try:
        request.validate()
        # If both location and language are missing, raise an error
        if request.location_ids is None and request.language_id is None:
            raise HTTPException(status_code=400, detail="Both 'location_ids' and 'language_id' must be provided.")
        
        keyword_json = query_keywords_description(prompt_keyword, request.keywords, request.description)
        # print(result)
        keyword = extract_keywords(str(keyword_json))
        
        if isinstance(keyword, tuple) and keyword[0] is False:
            raise HTTPException(status_code=400, detail=keyword[1])
        

        try:
            search_result = seo_keywords_main(
                keywords=keyword, 
                location_ids=request.location_ids, 
                language_id=request.language_id
            )
        except Exception as e:
            print(f"❌ Error in seo_keywords_main: {str(e)}")  
            raise HTTPException(status_code=500, detail="Failed to fetch keyword data from Google Ads API.")
        

        if not search_result or not isinstance(search_result, list):
            raise HTTPException(status_code=500, detail="Invalid response from Google Ads API.")

        # print(search_result)
        # print(request.branded_keyword)
        if request.exclude_values:
            search_result = filter_keywords_by_searches(search_result, request.exclude_values)
        
        if request.branded_words:
            search_result = filter_non_branded_keywords(search_result)
            search_result = remove_keywords(search_result)
            # print(search_result)

        if request.branded_keyword:
            # print("hello",request.branded_keyword)
            search_result = remove_branded_keywords(search_result,request.branded_keyword)
            add_keywords_to_json(request.branded_keyword)


        return search_result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@app.post("/seo_keyword_suggestion")
def seo_keyword_suggestion(request: SuggestionKeywordRequest):
    try:
        request.validate()
        keyword_json = query_keyword_suggestion(prompt_keyword_suggestion, request.keywords, request.description)
        print(keyword_json)
        # print(result)
        keyword =  (keyword_json)
        if keyword:
            return keyword
        else:
            return "Could you retry"
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    

@app.post("/seo_keyword_clustering")
async def seo_keyword_clustering(file: UploadFile = File(...)):
    try:
        if not file:
            return {"error": "No file uploaded"}
        # Read file contents and convert to DataFrame
        file_contents = await file.read()
        df = pd.read_csv(io.StringIO(file_contents.decode("utf-8")))  
        print({"COLUMNS":df.columns, "len":len(df)})

        df1 = df[["Keyword"]]

        print("Parsed DataFrame:", df1.head())
        data= df1.to_dict(orient="records")
        print("Parsed data:", data)
        cluster_data = await seo_main(df1.to_dict(orient="records"))  
        result = flatten_seo_data(cluster_data,df)

        return result
    except Exception as e:
        return {"error": str(e)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   
    


@app.post("/ppc_generate_keywords")
def ppc_generate_keywords(request: KeywordRequest):
    try:
        request.validate()
        # If both location and language are missing, raise an error
        if request.location_ids is None and request.language_id is None:
            raise HTTPException(status_code=400, detail="Both 'location_ids' and 'language_id' must be provided.")
        
        keyword_json = query_keywords_description(prompt_keyword, request.keywords, request.description)
        # print(result)
        keyword = extract_keywords(str(keyword_json))
        
        if isinstance(keyword, tuple) and keyword[0] is False:
            raise HTTPException(status_code=400, detail=keyword[1])
        

        try:
            search_result = ppc_keywords_main(
                keywords=keyword, 
                location_ids=request.location_ids, 
                language_id=request.language_id
            )
        except Exception as e:
            print(f"❌ Error in ppc_keywords_main: {str(e)}")  
            raise HTTPException(status_code=500, detail="Failed to fetch keyword data from Google Ads API.")
        

        if not search_result or not isinstance(search_result, list):
            raise HTTPException(status_code=500, detail="Invalid response from Google Ads API.")

        print(search_result)
        print(request.branded_keyword)
        if request.exclude_values:
            search_result = filter_keywords_by_searches(search_result, request.exclude_values)

        if request.branded_words:
            search_result = filter_non_branded_keywords(search_result)
            print(search_result)    

        if request.branded_keyword:
            search_result = remove_branded_keywords(search_result,request.branded_keyword,)    

        return search_result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    


@app.post("/ppc_keyword_clustering")
async def ppc_keyword_clustering(file: UploadFile = File(...)):
    try:

        if not file:
            return {"error": "No file uploaded"}
        # Read file contents and convert to DataFrame
        file_contents = await file.read()
        df = pd.read_csv(io.StringIO(file_contents.decode("utf-8")))  
        print({"COLUMNS":df.columns, "len":len(df)})

        df1 = df[["Keyword"]]

        print("Parsed DataFrame:", df1.head())
        data= df1.to_dict(orient="records")
        print("Parsed data:", data)  

        # result = asyncio.run(ppc_main(data))
        result = await ppc_main(data)
        ppc_data = flatten_ppc_data(result,df)
  
        return ppc_data


    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))     



# Soical media post
@app.post("/social_media_post")
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
    

#S3 bucket document upload
@app.post("/uploadfile")
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

   

@app.get("/list-documents/{user_id}/{category}")
async def list_documents(user_id: str, category: str):
    user = user_id
    category = category

    try:
        result = fetch_document_from_s3(user, category)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @app.post("/process-documents")
# async def process_documents(dict_data: DocumentData):
#     """FastAPI endpoint to process S3 documents and return extracted text as a dict."""
#     try:
#         text = download_document(dict_data.data)
#         print(text)
#         result = Document_summerizer(text)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))    



@app.post("/seo_uploadfile")
async def csv_seo_upload_file(file: UploadFile = File(...)):
      
    try:
        # Read file content
        file_content = await file.read()

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
        folder_name = "seo_content_generation"
        s3_path = upload_title_url(file_content, filename, folder_name)

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
    

# @app.post("/process_content_generation")
# async def process_content_generation(csv_data: CsvData):
#     """FastAPI endpoint to process S3 documents and return extracted text as a dict."""
#     try:
#         json_data = download_csv(csv_data.data)
#         print(json_data)
   
#         return json_data
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))     
    

@app.post("/blog_generation")
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


@app.post("/seo_based_blog")
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
