import yaml
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
load_dotenv()
# Define file paths
# CLIENT_SECRET_FILE = r"C:\Users\nickc\OneDrive\Desktop\AI marketing\google_ads\client_secret_783292392063-hfj4vc2836do2d8pjd3jgtbiieulckr9.apps.googleusercontent.com.json"
# YAML_FILE = r"C:\Users\nickc\OneDrive\Desktop\AI marketing\google_ads\google-ads.yaml"


# CLIENT_SECRET_FILE = r"/home/ubuntu/ai_marketing/google_ads/client_secret_783292392063-hfj4vc2836do2d8pjd3jgtbiieulckr9.apps.googleusercontent.com.json"
# YAML_FILE = r"/home/ubuntu/ai_marketing/google_ads/google-ads.yaml"

YAML_FILE_PATH = os.environ.get("YAML_FILE_PATH") 
CLIENT_SECRATE_FILE_PATH = os.environ.get("CLIENT_SECRATE_FILE_PATH")

def generate_refresh_token():
    try:
    
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRATE_FILE_PATH, 
            scopes=["https://www.googleapis.com/auth/adwords"]
        )
        
  
        credentials = flow.run_local_server(port=8080, access_type="offline", prompt="consent")
        
        # Extract tokens
        access_token = credentials.token
        refresh_token = credentials.refresh_token

        print("\n✅ New Tokens Generated:")
        print(f"🔹 Access Token: {access_token}")
        print(f"🔹 Refresh Token: {refresh_token}\n")

        # Update the google-ads.yaml file
        if refresh_token:
            update_yaml_file(refresh_token)

        return refresh_token

    except Exception as e:
        print(f"❌ Error generating refresh token: {e}")
        return None


def update_yaml_file(new_refresh_token):
    """ Updates the google-ads.yaml file with a new refresh token. """
    try:
        if os.path.exists(YAML_FILE_PATH):
            with open(YAML_FILE_PATH, "r") as file:
                config = yaml.safe_load(file)
            
            config["refresh_token"] = new_refresh_token  # Update the refresh token

            with open(YAML_FILE_PATH, "w") as file:
                yaml.dump(config, file, default_flow_style=False)
            
            print("✅ google-ads.yaml updated successfully!")
        else:
            print(f"⚠️ google-ads.yaml not found at: {YAML_FILE_PATH}")
    except Exception as e:
        print(f"❌ Error updating google-ads.yaml: {e}")

# Run the function
if __name__ == "__main__":
    generate_refresh_token()
