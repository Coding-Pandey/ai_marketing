from google.ads.googleads.client import GoogleAdsClient
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from google_ads.update_ref_token import generate_refresh_token
from dotenv import load_dotenv
load_dotenv()

YAML_FILE_PATH = os.environ.get("YAML_FILE_PATH") 

def get_client():
    try:
        client = GoogleAdsClient.load_from_storage(
            YAML_FILE_PATH,
            version="v18"
        )
        return client
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid_grant" in error_msg and ("expired" in error_msg or "revoked" in error_msg):
            print(f"❌ Refresh token is expired or revoked: {e}")
            print("🔄 Generating a new refresh token...")
            new_token = generate_refresh_token()
            if new_token:
                return get_client() 
            else:
                print("failed to generate refresh token")
                return None
            # return generate_refresh_token()
        else:
            print(f"Error in get_client: {e}")
            return False
        # print(f"Error in get_client: {e}")
        # return None


# get_client()