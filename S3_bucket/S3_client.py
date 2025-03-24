import boto3
import os
from dotenv import load_dotenv
load_dotenv()
aws_access = os.environ.get("AWS_ACCESS_KEY")
aws_secret = os.environ.get("AWS_SECRET_KEY")
s3_bucket_name = os.environ.get("BUCKET_NAME")


session = boto3.Session(
    aws_access_key_id=aws_access,
    aws_secret_access_key=aws_secret,
    region_name="us-east-1"  
)
s3 = session.client("s3")

