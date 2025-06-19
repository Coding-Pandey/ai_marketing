from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from auth.auth import get_db
from auth.models import SEOCluster ,SEOCSV, SEOFile
import json
import pandas as pd
import io
from .seo_models import KeywordRequest, SuggestionKeywordRequest, KeywordItem, UUIDRequest, PageUpdate, RemoveKeyword, KeywordClusterRequest, SEOFileNameUpdate
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
from S3_bucket.utile import upload_seo_table
from S3_bucket.delete_doc import seo_cluster_delete_document
from google_ads.seo_planner import seo_keywords_main
from Seo_process.Agents.Keyword_agent import query_keyword_suggestion,query_keywords_description
from Seo_process.Agents.clusterURL_keyword import seo_main
from Seo_process.prompts.keywords_prompt import prompt_keyword,prompt_keyword_suggestion
from S3_bucket.S3_upload import upload_title_url
from S3_bucket.fetch_document import  fetch_seo_cluster_file
from fastapi.responses import JSONResponse
from utils import verify_jwt_token, check_api_limit
from sqlalchemy.orm.attributes import flag_modified
from auth.auth import get_db
import uuid
import io
import json
from datetime import timedelta
from botocore.exceptions import ClientError

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
        # if request.exclude_values:
        #     search_result = filter_keywords_by_searches(search_result, request.exclude_values)
        
        # if request.branded_words:
        #     search_result = filter_non_branded_keywords(search_result)
        #     search_result = remove_keywords(search_result)
        #     # print(search_result)

        # if request.branded_keyword:
        #     # print("hello",request.branded_keyword)
        #     search_result = remove_branded_keywords(search_result,request.branded_keyword)
        #     add_keywords_to_json(request.branded_keyword)


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
async def seo_keyword_clustering(request: KeywordClusterRequest,
                                user= Depends(check_api_limit("seo_cluster")),
                                db: Session = Depends(get_db)
                                ):
    try:
        keywords = request.keywords
        delete_word = request.delete_word

        if not keywords:
            return {"error": "No keywords provided"}
        print(keywords)
        
        if delete_word and delete_word.branded_words:
            keywords = filter_non_branded_keywords(keywords)
            print(f"filter_non_branded_keywords: {keywords}")
            keywords = remove_keywords(keywords)
            print(f"remove_keywords: {keywords}")

        if delete_word and delete_word.branded_keyword:
            # print("hello",request.branded_keyword)
            keywords = remove_branded_keywords(keywords,delete_word.branded_keyword)
            # add_keywords_to_json(delete_word.branded_keyword)   
        # Read file contents and convert to DataFrame
        print("hello")
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

        

        if cluster_data and total_token:
         
            seo_cluster_record = db.query(SEOCluster).filter(SEOCluster.user_id == user.id).first()

            if seo_cluster_record:
                seo_cluster_record.total_tokens += total_token
            else:
                seo_cluster_record = SEOCluster(
                    user_id=user.id,
                    total_tokens=total_token
                )
                db.add(seo_cluster_record)

            db.commit()

        return result
    


    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   
    

@router.get("/seo_Clusterfiles_list")
async def seo_csv_documents(db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    try:
        user_id = int(id[1])  # Extract user_id from the JWT token
        seo_files = db.query(SEOFile).filter(SEOFile.user_id == user_id).all()
        if not seo_files:
            return []
        
        file_count = len(seo_files)


        # Fetch the SEOCSV record for last_reset value
        seo_csv_record = db.query(SEOCSV).filter(SEOCSV.user_id == user_id).first()

        if seo_csv_record:
        
            seo_csv_record.file_count = file_count
            seo_csv_record.call_count = file_count
            db.commit()

        # Include last_reset in each file entry
        result = [
            {
                "file_name": seo_file.file_name,
                "uuid": seo_file.uuid,
                "last_reset": seo_file.upload_time + timedelta(days=30) if seo_file.upload_time else None,
            }
            for seo_file in seo_files
        ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/seo_cluster_uploadfile")  
async def csv_seo_upload_file(json_data: dict = Body(...),
    id: str = Depends(verify_jwt_token),
    user=Depends(check_api_limit("seo_csv"))):
      
    try:
        
        # Read file content
        file_content = json_data.get("data", [])

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
        
        # data = convert_into_csvdata(file_content)
        # df = pd.DataFrame(data)
        # print(df.head())
        json_str = json.dumps(file_content)

        # Create a buffer for the JSON data
        json_buffer = io.StringIO(json_str)
        json_buffer.seek(0)

        # csv_buffer = io.StringIO()
        # df.to_csv(csv_buffer, index=False)
        # csv_buffer.seek(0)  # Go to start of buffer

        unique_id = uuid.uuid4().hex
        
        max_size = 10 * 1024 * 1024  
        if json_buffer.tell() > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds maximum limit of 10MB"
            )

   
        filename = json_data.get("fileName", None)

        if not filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )

     
        your_tuple = id
        user_id = your_tuple[1] 
        user_folder = f"User_{user_id}"
        # print(user_folder)
        # print(user_id)
        folder_name = "seo_clustering_data"

        s3_path = upload_title_url(user_folder, json_buffer.getvalue(), str(unique_id), folder_name)

        if s3_path is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to S3"
            )
        
        if s3_path:
            upload_seo_table(str(unique_id), user_id, filename, file_content )

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
    

@router.get("/seo_cluster_fetch_data/{uuid}")
async def seo_fetch_document(uuid: str, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    
    try:
        if uuid is None:
            raise HTTPException(status_code=200, detail="UUID is required")
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = str(uuid)  # Ensure uuid is a string
        seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=uuid).first()
     
        # print(f"json_data: {seo_file.json_data}")
        if not seo_file:
            raise HTTPException(status_code=200, detail="File not found for this user")
        
        data = fetch_seo_cluster_file(user_id, uuid)
        if not data:
            raise HTTPException(status_code=200, detail="No documents found for the user")
        
        json_data = json.loads(data["documents"])
        

        json_data = {
            "id": uuid,
            "fileName": seo_file.file_name,
            "data": seo_file.json_data
        }
        return json_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/seo_cluster_delete_document")
async def ppc_delete_document(request: UUIDRequest, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = request.uuid
        success = seo_cluster_delete_document(uuid, user_id)
        if success:
            # 2. Delete DB record
            user_id = int(id[1]) 
            file_record = db.query(SEOFile).filter_by(user_id=user_id, uuid=uuid).first()

            if file_record:
                db.delete(file_record)
                db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document deleted successfully",
                "uuid": uuid
            }
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete documents: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.delete("/seo-files/{seo_file_uuid}/keywords/{keyword_id}")
async def seo_delete_keyword(seo_file_uuid: str, keyword_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])  # Extract user_id from the JWT token
    seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
    # seo_file = db.query(SEOFile).filter(SEOFile.uuid == seo_file_uuid).first()
    if not seo_file:
        raise HTTPException(status_code=404, detail="SEO file not found")
    json_data = seo_file.json_data
    try:
        page_title_id, _ = keyword_id.split(".")
        print(page_title_id)
        print(keyword_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid keyword_id format")
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            keywords = page["Keywords"]
            print(keywords)
            for kw in keywords:
                if kw["Keyword_id"] == keyword_id:
                    keywords.remove(kw)
                    seo_file.json_data = json_data
                    print(seo_file.json_data)
                    flag_modified(seo_file, "json_data")
    
                    try:
                        db.commit()
                        db.refresh(seo_file)  # Refresh to confirm database state

                        return {"message": "Keyword deleted"}
                    except Exception as e:
    
                        db.rollback()
                        raise HTTPException(status_code=500, detail="Failed to save changes")
                    # return {"message": "Keyword deleted"}
            raise HTTPException(status_code=404, detail="Keyword not found")
    raise HTTPException(status_code=404, detail="Page not found")


@router.delete("/seo-files/{seo_file_uuid}/pages/{page_title_id}")
async def seo_delete_page(seo_file_uuid: str, page_title_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])
    seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
    if not seo_file:
        raise HTTPException(status_code=404, detail="SEO file not found")
    json_data = seo_file.json_data
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            json_data.remove(page)
            seo_file.json_data = json_data
            flag_modified(seo_file, "json_data")
            try:
                db.commit()
                db.refresh(seo_file) 
                return {"message": "Page deleted"} # Refresh to confirm database state
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to save changes")
    raise HTTPException(status_code=404, detail="Page not found")

# Edit a page by Page_title_id
@router.patch("/seo-files/{seo_file_uuid}/pages/{page_title_id}")
async def seo_edit_page(seo_file_uuid: str, page_title_id: str, page_update: PageUpdate, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):

    user_id = int(id[1])
    
    # Extract user_id from the JWT token    
    # seo_file = db.query(SEOFile).filter(SEOFile.uuid == seo_file_uuid).first()
    seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
    if not seo_file:
        raise HTTPException(status_code=404, detail="SEO file not found")
    json_data = seo_file.json_data
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            if page_update.Page_Title is not None:
                page["Page_Title"] = page_update.Page_Title
            if page_update.Suggested_URL_Structure is not None:
                page["Suggested_URL_Structure"] = page_update.Suggested_URL_Structure
            seo_file.json_data = json_data
            flag_modified(seo_file, "json_data")
            try:
                db.commit()
                db.refresh(seo_file)  # Refresh to confirm database state
                return {"message": "Page updated"}
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to save changes")
          
    raise HTTPException(status_code=404, detail="Page not found")



@router.patch("/seofile_name/{seo_file_uuid}")
async def seo_update_file_name(
    seo_file_uuid: str,
    payload: SEOFileNameUpdate,
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    user_id = int(id[1])
    seo_file = db.query(SEOFile).filter_by(user_id=user_id, uuid=seo_file_uuid).first()
    if not seo_file:
        raise HTTPException(status_code=404, detail="SEO file not found")
    
    seo_file.file_name = payload.file_name
    flag_modified(seo_file, "file_name")

    try:
        db.commit()
        db.refresh(seo_file)
        return {"message": "SEO file name updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes")
