from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
from Seo_process.Agents.Keyword_agent import query_keywords_description
from .ppc_models import KeywordRequest, KeywordItem
from Seo_process.prompts.keywords_prompt import prompt_keyword
from utils import (  
    extract_keywords,
    filter_keywords_by_searches,
    filter_non_branded_keywords,
    remove_branded_keywords,
    flatten_ppc_data,
    check_api_limit
)

from Ppc_process.Agents.structure_agent import ppc_main
from google_ads.ppc_process import ppc_keywords_main

router = APIRouter()



@router.post("/ppc_generate_keywords")
def ppc_generate_keywords(request: KeywordRequest,user=Depends(check_api_limit("ppc_keywords"))):
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
    


@router.post("/ppc_keyword_clustering")
async def ppc_keyword_clustering(keywords: List[KeywordItem],user=Depends(check_api_limit("ppc_cluster"))):
    try:

        if not keywords:
            return {"error": "No keywords provided"}
        
        # Convert keywords to DataFrame
        df = pd.DataFrame([k.dict() for k in keywords])
        print(df.head())
        print({"COLUMNS":df.columns, "len":len(df)})

        df1 = df[["Keyword"]]

        print("Parsed DataFrame:", df1.head())
        data= df1.to_dict(orient="records")
        print("Parsed data:", data)  

        # result = asyncio.run(ppc_main(data))
        result, total_token = await ppc_main(data)
        print("Result:", result)
        ppc_data = flatten_ppc_data(result,df)
  
        return ppc_data


    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))     
