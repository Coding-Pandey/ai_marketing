import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from S3_bucket.S3_client import s3
from botocore.exceptions import ClientError
from fastapi import HTTPException
from fastapi import UploadFile, HTTPException

S3_BUCKET_NAME = os.environ.get("BUCKET_NAME")
# user_folder = "User/"
S3_REGION = "us-east-1"
def upload_file_to_s3(user_folder: str, file_content: bytes, filename: str, category: str) -> str:
    """
    Upload file to S3 bucket under specified category folder
    Returns the S3 path of the uploaded file
    """
    try:
        # Construct S3 key with category as folder
        s3_key = f"{user_folder}/{category}/{filename}"
        
        # Upload file to S3
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            # ContentType='application/octet-stream'
        )
        
        # Construct S3 path
        s3_path = f"s3://{S3_BUCKET_NAME}/{s3_key}"

        return s3_path
        
    except ClientError as e:
        raise f"Failed to upload to S3: {str(e)}"
   

def upload_title_url(user_folder: str,file_content: bytes, filename: str, seo_content: str) -> str:
    try:
        # Construct S3 key with category as folder
        s3_key = f"{user_folder}/{seo_content}/{filename}"
        
        # Upload file to S3
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            # ContentType='application/octet-stream'
        )
        
        # Construct S3 path
        s3_path = f"s3://{S3_BUCKET_NAME}/{s3_key}"

        return s3_path
        
    except ClientError as e:
        raise f"Failed to upload to S3: {str(e)}"

def generate_presigned_url(key: str, expiration: int = 2592000) -> str:
    try:
        return s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate signed URL: {str(e)}")    

def upload_image_to_s3(image: UploadFile, file_path) -> str:
    try:
        file_extension = image.filename.split('.')[-1]
        unique_filename = f"{file_path}.{file_extension}"

        s3.upload_fileobj(
            image.file,
            S3_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": image.content_type}
        )
        image_url = generate_presigned_url(unique_filename)
        # image_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{unique_filename}"
        return image_url

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image to S3: {str(e)}")   

