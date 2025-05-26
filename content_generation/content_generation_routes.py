from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Form
from fastapi.responses import JSONResponse
from typing import Optional
from social_media.Agents.document_summared import Document_summerizer
from S3_bucket.fetch_document import download_document
from S3_bucket.fetch_document import download_document
from content_generation.blog_agent.blog_generation import blog_generation
from content_generation.blog_agent.blog_suggest import blog_suggest
from content_generation.blog_agent.seo_blog import generation_blog_async
from utils import verify_jwt_token, check_api_limit
import json
from auth.auth import get_db
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session
from auth.models import Contentgeneration, ContentgenerationFile
from datetime import timedelta
from content_generation.content_generation_model import UUIDRequest,ContentGenerationFileSchema
import uuid
import os


router = APIRouter()

content_types = [
    {"id": 1, "content_type": "blog generation"},
    {"id": 2, "content_type": "information post"},
    {"id": 3, "content_type": "press release and news pages"},
    {"id": 4, "content_type": "case study pages"},
    {"id": 5, "content_type": "FAQs"},
    {"id": 6, "content_type": "campaign landing pages"}, 
    {"id": 7, "content_type": "product descriptions"}  
]

@router.get("/content_types")
async def get_content_types():
    try:
        return {"content_types": content_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch content types: {str(e)}")

TEMP_FILE_DIR = "content_generation/tmp/uploads"  # Ensure this directory exists

@router.post("/content_generation")
async def content_generation(
    file: Optional[UploadFile] = File(None),
    text_data: Optional[str] = Form(None),
    content_type: Optional[int] = Form(None), 
    file_name: Optional[str] = Form(None),   
    objectives: Optional[str] = Form(None),
    audience: Optional[str] = Form(None),
    user=Depends(check_api_limit("content_generation")),
    db: Session = Depends(get_db),
    user_id: str = Depends(verify_jwt_token)
):
    try:
        user_id = int(user_id[1])  # Extract actual user ID from JWT payload

        # Validate required fields
        if not file_name:
            raise HTTPException(status_code=400, detail="File name is required")

        if not file and not text_data:
            raise HTTPException(status_code=400, detail="Either file or text_data must be provided")

        # Validate file format
        if file and not file.filename.lower().endswith((".docx", ".doc", ".pdf")):
            raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .docx, .doc, or .pdf file")

        # Validate content type
        allowed_content_types = [1]  # Expand this if needed
        if content_type and content_type not in allowed_content_types:
            raise HTTPException(status_code=400, detail="Invalid content type")

        # Handle file or text content
        if file:
            file_contents = await file.read()

            # Save file temporarily
            os.makedirs(TEMP_FILE_DIR, exist_ok=True)
            temp_file_path = os.path.join(TEMP_FILE_DIR, f"{uuid.uuid4().hex}_{file.filename}")
            with open(temp_file_path, "wb") as f:
                f.write(file_contents)

            temp_file_path = os.path.normpath(temp_file_path).replace("\\", "/")    

        else:
            file_contents = text_data.encode("utf-8")
            temp_file_path = None  # No physical file saved

        summarized_text_json = {}
        total_tokens = 0

        if content_type == 1:
            try:
                json_data, total_tokens = blog_generation(
                    file=file_contents,
                    json_data=summarized_text_json
                )

                # Update user token usage
                content_gen_record = db.query(Contentgeneration).filter(Contentgeneration.user_id == user_id).first()
                if content_gen_record:
                    if total_tokens > 0:
                        content_gen_record.total_tokens += total_tokens
                    if not json_data:
                        content_gen_record.call_count = max(content_gen_record.call_count - 1, 0)
                    db.commit()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Blog generation failed: {str(e)}")

        return JSONResponse(content={
            "filename": file_name,
            "content_type": "blog generation",
            "data": json_data,
            "temp_file_path": temp_file_path  # Send this if you want to reuse the file
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")

@router.get("/content_datalist")
async def content_documents(db: Session = Depends(get_db), id: str = Depends(verify_jwt_token)):
    try:
        user_id = int(id[1])  
        content_files = db.query(ContentgenerationFile).filter(ContentgenerationFile.user_id == user_id).all()
        if not content_files:
            return []

        file_count = len(content_files)


        content_record = db.query(Contentgeneration).filter(Contentgeneration.user_id == user_id).first()

        if content_record:

            content_record.file_count = file_count
            content_record.call_count = file_count
            db.commit()

   
        result = [
            {
                "file_name": content_file.file_name,
                "uuid": content_file.uuid,
                "last_reset": content_file.last_reset + timedelta(days=30) if content_file.last_reset else None,
            }
            for content_file in content_files
        ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    

@router.delete("/content_delete_data")
async def content_delete_data(request: UUIDRequest, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        user_id = str(id[1])  # Extract user_id from the JWT token
        uuid = request.uuid
        # success = seo_cluster_delete_document(uuid, user_id)
        # if success:
            # 2. Delete DB record
        user_id = int(id[1]) 
        file_record = db.query(ContentgenerationFile).filter_by(user_id=user_id, uuid=uuid).first()

        if file_record:
            db.delete(file_record)
            db.commit()
            # db.refresh(file_record) 

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document deleted successfully",
                "uuid": uuid
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   
    except Exception as e:
        db.rollback()
        raise Exception(f"Error storing file in table: {str(e)}")
    finally:
        db.close()  

@router.get("/content_data/{uuid}")
async def content_fetch_data(uuid: str, id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        if uuid is None:
            raise HTTPException(status_code=200, detail="UUID is required")
        user_id = str(id[1]) 
        print(user_id) # Extract user_id from the JWT token
        uuid = str(uuid)  # Ensure uuid is a string
        file = db.query(ContentgenerationFile).filter_by(user_id=user_id, uuid=uuid).first()

        # print(f"json_data: {seo_file.json_data}")
        if not file:
            raise HTTPException(status_code=200, detail="File not found for this user")
        
        # data = fetch_seo_cluster_file(user_id, uuid)
        # if not data:
        #     raise HTTPException(status_code=200, detail="No documents found for the user")
        
        # json_data = json.loads(data["documents"])
        

        json_data = {
            "id": uuid,
            "filename": file.file_name,
            "content_type": file.content_type,
            "data":  file.content_data
        }
        return json_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/content_generation_uploadfile/{uuid}")
async def content_generation_upload_file(
    json_data: ContentGenerationFileSchema = Body(...),
    uuid: Optional[str] = None,
    id: str = Depends(verify_jwt_token),
    temp_file_path: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        # Extract user_id from JWT token
        user_id = id[1]  # Assuming it's a tuple like (status, user_id)

        if uuid:
            db_query = db.query(ContentgenerationFile).filter(ContentgenerationFile.uuid == uuid)
            content_generation = db_query.first()

            if not content_generation:
                raise HTTPException(status_code=404, detail="Record not found for provided UUID.")

            # Update existing entry
            content_generation.content_data = json_data.data
            flag_modified(content_generation, "content_data")
            db.commit()
            db.refresh(content_generation)

            return JSONResponse(
                status_code=200,
                content={"message": "File updated successfully", "uuid": uuid}
            )

        else:
            # Validation
            file_content = json_data.data
            file_name = json_data.filename
            content_type = json_data.content_type

            if not file_content:
                raise HTTPException(status_code=400, detail="No data provided")
            if not file_name:
                raise HTTPException(status_code=400, detail="No filename provided")
            if not content_type:
                raise HTTPException(status_code=400, detail="No content type provided")

            # Create new entry
            unique_id = uuid.uuid4().hex

            content_generation = ContentgenerationFile(
                user_id=user_id,
                file_name=file_name,
                uuid=unique_id,
                content_type=content_type,
                content_data=file_content
            )

            db.add(content_generation)
            flag_modified(content_generation, "content_data")
            db.commit()
            db.refresh(content_generation)

            return JSONResponse(
                status_code=200,
                content={
                    "message": "File uploaded successfully",
                    "uuid": unique_id,
                    "filename": file_name,
                    "content_type": content_type
                }
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        # Safe temp file deletion
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as cleanup_error:
                # Optional: log cleanup failure
                print(f"Failed to remove temp file: {cleanup_error}")

        else:
            print("No temp file to delete or file does not exist.")        



@router.post("/blog_suggestion_more")
async def blog_suggestion_more(
    file: Optional[UploadFile] = File(None),
    text_data: Optional[str] = Form(None),
    generated_blog: Optional[str] = Form(None),
    # user = Depends(check_api_limit("content_generation")),
    db: Session = Depends(get_db),
    user_id: str = Depends(verify_jwt_token)   # Renamed to be more descriptive
):
    try:
        user_id = int(user_id[1])  # Extract user_id from the JWT token
        # Validate inputs

        if not file and not text_data:
            raise HTTPException(status_code=400, detail="Either file or text_data must be provided")

        # Validate file format
        if file and not file.filename.lower().endswith((".docx", ".doc", ".pdf")):
            raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .docx, .doc, or .pdf file")

        # Process file or text data
        file_contents = await file.read() if file else text_data.encode('utf-8')
        
        # Initialize variables
        summarized_text_json = {}
        total_token = 0
        try:
            # Assuming blog_generation returns JSON data and token count
            json_data, total_tokens = blog_suggest(
                file=file_contents,
                Generated_Blog=generated_blog,
                json_data=summarized_text_json
            )
            total_token += total_tokens

            return json_data

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Blog generation failed: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.patch("/update_name_and_title/{uuid}")
async def update_name_and_title(
    uuid: str,
    new_filename: Optional[str] = Body(None),
    new_title: Optional[str] = Body(None),
    id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        user_id = int(id[1])

        content_file = db.query(ContentgenerationFile).filter(
            ContentgenerationFile.uuid == uuid,
            ContentgenerationFile.user_id == user_id
        ).first()

        if not content_file:
            raise HTTPException(status_code=404, detail="File not found")

        # If neither field is sent, raise error
        if not new_filename and not new_title:
            raise HTTPException(status_code=400, detail="At least one of new_filename or new_title must be provided")

        if new_filename and new_filename.strip():
            content_file.file_name = new_filename

        if new_title and new_title.strip():
            if isinstance(content_file.content_data, dict):
                content_file.content_data["Title"] = new_title
                flag_modified(content_file, "content_data")
            else:
                raise HTTPException(status_code=500, detail="content_data is not a valid JSON object")

        db.commit()
        db.refresh(content_file)

        return {
            "message": "Update successful",
            "new_filename": content_file.file_name,
            "new_title": content_file.content_data.get("Title", None)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# @router.post("/seo_based_blog")
# async def Seo_based_blog(csv_data: str = Form(...), text: Optional[str] = Form(None)):
#     try:
#         parsed_data = json.loads(csv_data) 
#         # print(parsed_data)
#         json_data = download_csv(parsed_data['data'])
#         # print(json_data)
#         keywords = [item['keyword'] for item in json_data['csv']]
#         new_blog ,total_tokens_used = await generation_blog_async(keywords, text)
#         print(f"total Seo blog {total_tokens_used}")
#         return new_blog, total_tokens_used

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))    

