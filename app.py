# from chatbot import PROMPT, query_llm, prompt_keyword_suggestion, query_keyword_suggestion
import pandas as pd
from fastapi import FastAPI, HTTPException, File, UploadFile, Query
from pydantic import BaseModel
from typing import Optional
import json
from Seo_process.Agents.Keyword_agent import query_keyword_suggestion,query_keywords_description
from Seo_process.Agents.clusterURL_keyword import seo_main
from Ppc_process.Agents.structure_agent import ppc_main
from Seo_process.prompts.keywords_prompt import prompt_keyword,prompt_keyword_suggestion
from collections import defaultdict
from google_ads.seo_planner import seo_keywords_main
from google_ads.ppc_process import ppc_keywords_main
# from utils import flatten_seo_data , extract_first_json_object
import asyncio
from utils import flatten_seo_data , extract_keywords, filter_keywords_by_searches, flatten_ppc_data, remove_branded_keywords, filter_non_branded_keywords
import io
from pydantic import BaseModel, Field
from typing import Optional, List
app = FastAPI()


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
            print(search_result)

        if request.branded_keyword:
            search_result = remove_branded_keywords(search_result,request.branded_keyword,)

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
