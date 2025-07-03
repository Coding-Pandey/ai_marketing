from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from auth.auth import get_db
from auth.models import  PPCCluster, PPCFile, PPCCSV
from typing import List
import pandas as pd
import io
from Seo_process.Agents.Keyword_agent import query_keywords_description
from .ppc_models import KeywordRequest, KeywordItem, ppcPageUpdate, UUIDRequest, KeywordClusterRequest, PPCFileNameUpdate
from Seo_process.prompts.keywords_prompt import prompt_keyword
from utils import (  
    extract_keywords,
    filter_keywords_by_searches,
    filter_non_branded_keywords,
    remove_branded_keywords,
    flatten_ppc_data,
    check_api_limit,
    filter_by_branded,
    remove_keywords,
    add_keywords_to_json
)

from Ppc_process.Agents.structure_agent import ppc_main
from google_ads.ppc_process import ppc_keywords_main

from S3_bucket.S3_upload import upload_title_url
from sqlalchemy.orm import Session
from S3_bucket.fetch_document import fetch_ppc_cluster_file
from fastapi.responses import JSONResponse
from fastapi import Body
from utils import verify_jwt_token, check_api_limit
from S3_bucket.utile import  upload_ppc_table
from S3_bucket.delete_doc import  ppc_cluster_delete_document
from sqlalchemy.orm.attributes import flag_modified
from auth.auth import get_db
from botocore.exceptions import ClientError
import pandas as pd
import uuid
import json
from datetime import datetime, timedelta



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
                keywords = keyword, 
                location_ids = [loc.id for loc in request.location_ids], 
                language_id = request.language_id.ID if request.language_id else None 
            )
        except Exception as e:
            print(f"❌ Error in ppc_keywords_main: {str(e)}")  
            raise HTTPException(status_code=500, detail="Failed to fetch keyword data from Google Ads API.")
        

        if not search_result or not isinstance(search_result, list):
            raise HTTPException(status_code=500, detail="Invalid response from Google Ads API.")

        # print(search_result)
        # print(request.branded_keyword)
        # if request.exclude_values:
        #     search_result = filter_keywords_by_searches(search_result, request.exclude_values)

        # if request.branded_words:
        #     search_result = filter_non_branded_keywords(search_result)
        #     print(search_result)    

        # if request.branded_keyword:
        #     search_result = remove_branded_keywords(search_result,request.branded_keyword,)    

        return search_result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/ppc_keyword_clustering")
async def ppc_keyword_clustering(request: KeywordClusterRequest
                                 ,user=Depends(check_api_limit("ppc_cluster")), 
                                   db: Session = Depends(get_db),
                                     id: str = Depends(verify_jwt_token)):
    try:

        keywords = request.keywords
        delete_word = request.delete_word

        if not keywords:
            return {"error": "No keywords provided"}
        
        if delete_word and delete_word.exclude:
            # keywords = filter_non_branded_keywords(keywords)
            # keywords = remove_keywords(keywords)
            # keywords = remove_branded_keywords(keywords,delete_word.branded_keyword)
            keywords = filter_by_branded(keywords, delete_word.exclude, include=False)

        if delete_word and delete_word.include:
            keywords = filter_by_branded(keywords, delete_word.include, include=True)
            # print("hello",request.branded_keyword)
            # add_keywords_to_json(delete_word.branded_keyword)  
        
        # Convert keywords to DataFrame
        df = pd.DataFrame([k.dict() for k in keywords])
        print(df.head())
        print({"COLUMNS":df.columns, "len":len(df)})

        df1 = df[["Keyword"]]

        print("Parsed DataFrame:", df1.head())
        data= df1.to_dict(orient="records")
        print("Parsed data:", data)  

        # result = asyncio.run(ppc_main(data))
        cluster_data, total_token = await ppc_main(data)
        print("Result:", cluster_data)
        ppc_data = flatten_ppc_data(cluster_data,df)
        if cluster_data and total_token:
            unique_id = uuid.uuid4().hex
            filename = request.file_name
            user_id = int(id[1]) 

            if ppc_data:
                location_data = [loc.dict() for loc in request.location_ids]
                language_data = request.language_id.dict() if request.language_id else None
                upload_ppc_table(str(unique_id), user_id, filename, ppc_data, location_data, language_data)
         
            ppc_cluster_record = db.query(PPCCluster).filter(PPCCluster.user_id == user.id).first()

            if ppc_cluster_record:
                ppc_cluster_record.total_tokens += total_token
            else:
                ppc_cluster_record = PPCCluster(
                    user_id=user.id,
                    total_tokens=total_token,
                    call_count=1
                )
                db.add(ppc_cluster_record)

            db.commit()

        return JSONResponse(
                    status_code=200,
                    content={
                        "message": "PPC clustering completed successfully",
                        "uuid": unique_id,
                        "filename": filename
                    }
                )
    


    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))     


@router.get("/ppc_Clusterfiles_list")
async def ppc_csv_documents(db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    try:
        user_id = int(id[1])  # Extract user_id from the JWT token
        
        # Get current time
        current_time = datetime.now()
        
        # Get all PPC files for the user
        ppc_files = db.query(PPCFile).filter(PPCFile.user_id == user_id).all()
        
        # Check for expired files and remove them
        expired_files = []
        active_files = []
        
        for ppc_file in ppc_files:
            if ppc_file.upload_time:
                # Calculate expiry date (30 days from upload)
                expiry_date = ppc_file.upload_time + timedelta(days=30)
                
                if current_time >= expiry_date:
                    # File has expired, mark for deletion
                    expired_files.append(ppc_file)
                else:
                    # File is still active
                    active_files.append(ppc_file)
            else:
                # If no upload_time, keep the file (or handle as needed)
                active_files.append(ppc_file)
        
        # Remove expired files from database
        if expired_files:
            for expired_file in expired_files:
                db.delete(expired_file)
            db.commit()
            print(f"Removed {len(expired_files)} expired files for user {user_id}")
        
        # If no active files remain, return empty list
        if not active_files:
            # Update PPCCSV record to reflect zero files
            ppc_csv_record = db.query(PPCCSV).filter(PPCCSV.user_id == user_id).first()
            if ppc_csv_record:
                ppc_csv_record.file_count = 0
                ppc_csv_record.call_count = 0
                db.commit()
            return []
        
        # Update file_count and call_count with active files
        file_count = len(active_files)
        ppc_csv_record = db.query(PPCCSV).filter(PPCCSV.user_id == user_id).first()
        if ppc_csv_record:
            ppc_csv_record.file_count = file_count
            ppc_csv_record.call_count = file_count
            db.commit()
        
        # Return active files with last_reset information
        result = [
            {
                "file_name": ppc_file.file_name,
                "uuid": ppc_file.uuid,
                "last_reset": ppc_file.upload_time + timedelta(days=30) if ppc_file.upload_time else None,
            }
            for ppc_file in active_files
        ]
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ppc_cluster_uploadfile")
async def csv_ppc_upload_file(json_data: dict = Body(...),
    id: str = Depends(verify_jwt_token),
    user=Depends(check_api_limit("ppc_csv"))):
      
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
        folder_name = "ppc_clustering_data"

        s3_path = upload_title_url(user_folder, json_buffer.getvalue(), str(unique_id), folder_name)

        if s3_path is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to S3"
            )
        
        if s3_path:
            upload_ppc_table(str(unique_id), user_id, filename, file_content)

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
    
@router.get("/ppc_cluster_fetch_data/{uuid}")
async def ppc_fetch_document(uuid: str, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        if uuid is None:
            raise HTTPException(status_code=200, detail="UUID is required")
        user_id = str(id[1]) 
        uuid = str(uuid) 
        ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=uuid).first()
        if not ppc_file:
            raise HTTPException(status_code=200, detail="File not found for this user")
        # data = fetch_ppc_cluster_file(user_id, uuid)
        # if not data:
        #     raise HTTPException(status_code=200, detail="No documents found for the user")
        # json_data = json.loads(data["documents"])

        json_data = {
            "id": uuid,
            "fileName": ppc_file.file_name,
            "data": ppc_file.json_data
        }
        return json_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ppc_cluster_delete_document")
async def ppc_delete_document(request: UUIDRequest, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        user_id = str(id[1]) 
        uuid = request.uuid
        # success = ppc_cluster_delete_document(uuid, user_id)
        # if success:
        
        user_id = int(id[1]) 
        file_record = db.query(PPCFile).filter_by(user_id=user_id, uuid=uuid).first()

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

@router.delete("/ppc-files/{ppc_file_uuid}/keywords/{keyword_id}")
def ppc_delete_keyword(ppc_file_uuid: str, keyword_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])  # Extract user_id from the JWT token
    ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=ppc_file_uuid).first()
    if not ppc_file:
        raise HTTPException(status_code=404, detail="PPC file not found")
    json_data = ppc_file.json_data
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
                    ppc_file.json_data = json_data
                    # print(ppc_file.json_data)
                    flag_modified(ppc_file, "json_data")
    
                    try:
                        db.commit()
                        db.refresh(ppc_file)  # Refresh to confirm database state

                        return {"message": "Keyword deleted"}
                    except Exception as e:
    
                        db.rollback()
                        raise HTTPException(status_code=500, detail="Failed to save changes")
                    # return {"message": "Keyword deleted"}
            raise HTTPException(status_code=404, detail="Keyword not found")
    raise HTTPException(status_code=404, detail="Page not found")


@router.delete("/ppc-files/{ppc_file_uuid}/pages/{page_title_id}")
def ppc_delete_page(ppc_file_uuid: str, page_title_id: str, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    user_id = int(id[1])
    ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=ppc_file_uuid).first()
    if not ppc_file:
        raise HTTPException(status_code=404, detail="PPC file not found")
    json_data = ppc_file.json_data
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            json_data.remove(page)
            ppc_file.json_data = json_data
            flag_modified(ppc_file, "json_data")
            try:
                db.commit()
                db.refresh(ppc_file) 
                return {"message": "Page deleted"} 
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to save changes")
    raise HTTPException(status_code=404, detail="Page not found")


@router.patch("/ppc-files/{ppc_file_uuid}/pages/{page_title_id}")
def ppc_edit_page(ppc_file_uuid: str, page_title_id: str, page_update: ppcPageUpdate, db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):

    user_id = int(id[1])
    # Extract user_id from the JWT token    
    ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=ppc_file_uuid).first()
    if not ppc_file:
        raise HTTPException(status_code=404, detail="PPC file not found")
    
    json_data = ppc_file.json_data
    page_found = False
    
    for page in json_data:
        if page["Page_title_id"] == page_title_id:
            page_found = True
            # Update Ad_Group if provided
            if page_update.Ad_Group is not None:
                page["Ad_Group"] = page_update.Ad_Group
            
            if page_update.Descriptions:
                for desc_update in page_update.Descriptions:
                    if isinstance(desc_update, str):
                        continue  # skip if it's a string and not an object
                    found = False
                    for ad_group in json_data if isinstance(json_data, list) else [json_data]:
                        for description in ad_group.get("Descriptions", []):
                            if description.get("Description_id") == desc_update.Description_id:
                                description["Description"] = desc_update.Description
                                found = True
                                break
                        if found:
                            break
                    if not found:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Description with ID {desc_update.Description_id} not found"
                        )
        
            if page_update.Ad_Headlines:
                for headline_update in page_update.Ad_Headlines:
                    if isinstance(headline_update, str):
                        continue
                    found = False
                    for ad_group in json_data if isinstance(json_data, list) else [json_data]:
                        for headline in ad_group.get("Ad_Headlines", []):
                            if headline.get("Headlines_id") == headline_update.Headlines_id:
                                headline["Ad_Headline"] = headline_update.Ad_Headline
                                found = True
                                break
                        if found:
                            break
                    if not found:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Headline with ID {headline_update.Headlines_id} not found"
                        )
                
            # Save changes to database
            ppc_file.json_data = json_data
            flag_modified(ppc_file, "json_data")
            try:
                db.commit()
                db.refresh(ppc_file)  # Refresh to confirm database state
                return {"message": "Page updated successfully"}
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}")
    
    if not page_found:
        raise HTTPException(status_code=404, detail="Page not found")
    

@router.patch("/ppcfile_name/{ppc_file_uuid}")
async def ppc_update_file_name(
    ppc_file_uuid: str,
    payload: PPCFileNameUpdate,
    db: Session = Depends(get_db),
    id: str = Depends(verify_jwt_token)
):
    user_id = int(id[1])
    ppc_file = db.query(PPCFile).filter_by(user_id=user_id, uuid=ppc_file_uuid).first()
    if not ppc_file:
        raise HTTPException(status_code=404, detail="PPC file not found")

    ppc_file.file_name = payload.file_name
    flag_modified(ppc_file, "file_name")

    try:
        db.commit()
        db.refresh(ppc_file)
        return {"message": "PPC file name updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes : " + str(e))


