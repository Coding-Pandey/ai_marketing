from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from auth.auth import get_db
import json
import pandas as pd
import io
from .seo_models import KeywordRequest, SuggestionKeywordRequest, KeywordItem
from utils import (  
    extract_keywords,
    filter_keywords_by_searches,
    filter_non_branded_keywords,
    remove_keywords,
    remove_branded_keywords,
    add_keywords_to_json,
    flatten_seo_data,
    check_api_limit,
    map_seo_pages_with_search_volume
)

from google_ads.seo_planner import seo_keywords_main
from Seo_process.Agents.Keyword_agent import query_keyword_suggestion,query_keywords_description
from Seo_process.Agents.clusterURL_keyword import seo_main
from Seo_process.prompts.keywords_prompt import prompt_keyword,prompt_keyword_suggestion


router = APIRouter()

@router.post("/seo_generate_keywords")
def seo_generate_keywords(request: KeywordRequest, user=Depends(check_api_limit("seo_keywords")),
    db: Session = Depends(get_db)):
    try:
        request.validate()
        # If both location and language are missing, raise an error
        if request.location_ids is None and request.language_id is None:
            raise HTTPException(status_code=400, detail="Both 'location_ids' and 'language_id' must be provided.")

        if request.description:
            keyword_json = query_keywords_description(prompt_keyword, request.keywords, request.description)
  
        else:
            keywords_list = [kw.strip() for kw in request.keywords.split(",")] if request.keywords else []
            keyword_json = {"keywords": keywords_list}
            keyword_json = json.dumps(keyword_json) 
            print(f"keyword json: {keyword_json}")
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
    

@router.post("/seo_keyword_suggestion")
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
    


@router.post("/seo_keyword_clustering")
async def seo_keyword_clustering( keywords: List[KeywordItem], user=Depends(check_api_limit("seo_cluster"))):
    try:
        if not keywords:
            return {"error": "No keywords provided"}
        # Read file contents and convert to DataFrame
        df = pd.DataFrame([k.dict() for k in keywords]) 
        print({"COLUMNS":df.columns, "len":len(df)})

        df1 = df[["Keyword"]]

        print("Parsed DataFrame:", df1.head())
        data= df1.to_dict(orient="records")
        print("Parsed data:", data)
        cluster_data, total_token  = await seo_main(df1.to_dict(orient="records")) 
        print("Clustered data:", cluster_data) 
        # result = flatten_seo_data(cluster_data,df)
        result = map_seo_pages_with_search_volume(cluster_data, df)

        return result , total_token
    


    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   
    
