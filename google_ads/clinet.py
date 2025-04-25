from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.oauth2 import service_account
import os
from dotenv import load_dotenv
load_dotenv()

YAML_FILE_PATH = os.environ.get("YAML_FILE_PATH") 

# def get_client():
#     try:
#         client = GoogleAdsClient.load_from_storage(
#             YAML_FILE_PATH,
#             version="v18"
#         )
#         return client
#     except Exception as e:
#         error_msg = str(e).lower()
#         if "invalid_grant" in error_msg and ("expired" in error_msg or "revoked" in error_msg):
#             print(f"❌ Refresh token is expired or revoked: {e}")
#             print("🔄 Generating a new refresh token...")
#             new_token = generate_refresh_token()
#             if new_token:
#                 return get_client() 
#             else:
#                 print("failed to generate refresh token")
#                 return None
#             # return generate_refresh_token()
#         else:
#             print(f"Error in get_client: {e}")
#             return False
        # print(f"Error in get_client: {e}")
        # return None


# get_client()
def get_client():
    """Create and return a Google Ads API client using service account credentials."""
    # Get the path to the service account JSON key file
    SERVICE_ACCOUNT_FILE = os.environ.get("SERVICE_ACCOUNT_FILE")

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise ValueError(f"Service account file not found at: {SERVICE_ACCOUNT_FILE}")
    
    # Load credentials from the service account file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/adwords']
    )
    
    # Developer token - in production, this should be in env variables
    DEVELOPER_TOKEN = os.environ.get("DEVELOPER_TOKEN")
    
    # Retrieve the customer ID from an environment variable
    CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
    if not CUSTOMER_ID:
        raise ValueError("Customer ID must be set in environment variable GOOGLE_ADS_CUSTOMER_ID")
    
    # Initialize and return the GoogleAdsClient
    return GoogleAdsClient(
        credentials=credentials,
        developer_token=DEVELOPER_TOKEN,
        use_proto_plus=True,
        login_customer_id=CUSTOMER_ID
    )