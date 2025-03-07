# from chatbot import PROMPT, query_llm, prompt_keyword_suggestion, query_keyword_suggestion
import pandas as pd
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Optional
import json
from Seo_process.Agents.Keyword_agent import query_keyword_suggestion,query_keywords_description
from Seo_process.Agents.clusterURL_keyword import seo_main
from Ppc_process.Agents.structure_agent import ppc_main
from Seo_process.prompts.keywords_prompt import prompt_keyword,prompt_keyword_suggestion
from collections import defaultdict
from google_ads.seo_planner import seo_keywords_main
# from utils import flatten_seo_data , extract_first_json_object
import asyncio
from utils import flatten_seo_data
import io

app = FastAPI()

def extract_keywords(json_string):
    """Validate JSON and extract 'keywords' list if present."""
    try:
        if isinstance(json_string, dict):  # If already a dictionary, use it directly
            parsed_json = json_string
        else:
            parsed_json = json.loads(json_string)  # Try parsing JSON string

        if "keywords" in parsed_json and isinstance(parsed_json["keywords"], list):
            return parsed_json["keywords"]  # Return keywords if valid
        else:
            return False, "'keywords' field is missing or not a list."
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"  # Return JSON parsing error


def Seo_keyword_search(keywords: list ) -> str:
    # Lod CSV file
    # csv_file = r""  # Replace with your file path
    # df = pd.read_csv(csv_file)
    # # Convert DataFrame to JSON
    # json_data = df.to_json(orient="records", indent=4)
    print(keywords)
    json_data = seo_keywords_main(keywords)

    return json_data    


class KeywordRequest(BaseModel):
    keywords: Optional[str] = None
    description: Optional[str] = None

    def validate(self):
        if not self.keywords and not self.description:
            raise ValueError("At least one of 'keywords' or 'description' must be provided")
        


@app.post("/seo_generate_keywords")
def seo_generate_keywords(request: KeywordRequest):
    try:
        request.validate()
        keyword_json = query_keywords_description(prompt_keyword, request.keywords, request.description)
        # print(result)
        keyword = extract_keywords(str(keyword_json))
       
        if keyword:
            result = Seo_keyword_search(keywords=keyword)
            return result
        else:
            return keyword
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing request")
    

@app.post("/seo_keyword_suggestion")
def seo_keyword_suggestion(request: KeywordRequest):
    try:
        request.validate()
        keyword_json = query_keyword_suggestion(prompt_keyword_suggestion, request.keywords, request.description)
        print(keyword_json)
        # print(result)
        keyword = extract_keywords(keyword_json)
        if keyword:
            return keyword
        else:
            return "Could you retry"
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing request")    
    

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
        result = flatten_seo_data(cluster_data)

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
        keyword_json = query_keywords_description(prompt_keyword, request.keywords, request.description)
        # print(result)
        keyword = extract_keywords(str(keyword_json))
       
        if keyword:
            result = Seo_keyword_search(keywords=keyword)
            return result
        else:
            return keyword
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing request")
    

@app.post("/ppc_keyword_suggestion")
def ppc_keyword_suggestion(request: KeywordRequest):
    try:
        request.validate()
        keyword_json = query_keyword_suggestion(prompt_keyword_suggestion, request.keywords, request.description)
        print(keyword_json)
        # print(result)
        keyword = extract_keywords(keyword_json)
        if keyword:
            return keyword
        else:
            return "Could you retry"
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing request")    
    

@app.post("/ppc_keyword_clustering")
async def ppc_keyword_clustering(file: UploadFile = File(...)):
    try:

        # file_contents = file.file.read()
        # print("File contents:", file_contents)  
        file_extension = file.filename.split(".")[-1].lower()
        
        if file_extension == "csv":
            df = pd.read_csv(file.file)
        elif file_extension in ["xls", "xlsx"]:
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a CSV or Excel file.")
        
        df1 = df[["Keyword"]]      
        data = df1.to_dict(orient="records")
        print("Parsed data:", data)  

        result = asyncio.run(ppc_main(data))
  
        return result


    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))     