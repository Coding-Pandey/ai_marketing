import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from S3_bucket.S3_client import s3
from fastapi import HTTPException
from botocore.exceptions import ClientError

S3_BUCKET_NAME = os.environ.get("BUCKET_NAME")
user_folder = "User/"


def seo_cluster_delete_document(uuid: str, id: str) -> dict:
    try:
        user_id = f"User_{id}"
        category = "seo_clustering_data"
        prefix = f"{user_id}/{category}/{uuid}"

        # List all objects under the UUID folder
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)

        if "Contents" not in response or not response["Contents"]:
            raise HTTPException(status_code=404, detail="No documents found to delete")

        # Create delete objects list
        delete_keys = [{"Key": obj["Key"]} for obj in response["Contents"]]

        # Perform the deletion
        s3.delete_objects(
            Bucket=S3_BUCKET_NAME,
            Delete={"Objects": delete_keys}
        )

        return True

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete from S3: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



# seo_cluster_delete_document("543e82dd5632494b955be1f76b19247b", "3")