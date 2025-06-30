import requests
import os
from typing import Optional


def fetch_linkedin_urn(access_token: str) -> str:
    """Returns the `urn:li:person:{id}` string for this user."""
    # Try OpenID Connect userinfo endpoint first (works with 'openid profile' scope)
    try:
        userinfo_resp = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        userinfo_resp.raise_for_status()
        userinfo_data = userinfo_resp.json()
        print(f"UserInfo response: {userinfo_data}")  # Debug output
        
        # Extract person ID from the 'sub' field
        # 'sub' should be like 'urn:li:person:A1B2C3D4E5'
        sub_value = userinfo_data.get('sub')
        if sub_value and sub_value.startswith('urn:li:person:'):
            return sub_value
        else:
            # Sometimes sub might just be the ID without the URN prefix
            person_id = sub_value
            return f"urn:li:person:{person_id}"
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("OpenID userinfo failed, trying REST API...")
        else:
            raise
    
    # Fallback to REST API (requires r_liteprofile scope)
    me_resp = requests.get(
        "https://api.linkedin.com/v2/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
    )
    me_resp.raise_for_status()
    me_data = me_resp.json()
    print(f"Profile response: {me_data}")  # Debug output
    # me_data["id"] is something like "A1B2C3D4E5"
    return f"urn:li:person:{me_data['id']}"


def upload_image_to_linkedin(access_token: str, author_urn: str, image_url: str) -> str:
    """
    Upload an image from URL to LinkedIn and return the asset URN.
    
    Args:
        access_token: OAuth2 bearer token with w_member_social scope
        author_urn: The author's URN (e.g., "urn:li:person:...")
        image_url: URL of the image to upload
        
    Returns:
        The LinkedIn asset URN for the uploaded image
    """
    # Step 1: Register the upload
    register_upload_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }
    
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author_urn,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    
    print("Registering upload...")
    register_resp = requests.post(register_upload_url, json=register_payload, headers=headers)
    register_resp.raise_for_status()
    register_data = register_resp.json()
    
    # Extract upload URL and asset URN
    upload_mechanism = register_data["value"]["uploadMechanism"]
    upload_url = upload_mechanism["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn = register_data["value"]["asset"]
    
    print(f"Upload URL obtained: {upload_url}")
    print(f"Asset URN: {asset_urn}")
    
    # Step 2: Download the image from the provided URL
    print(f"Downloading image from: {image_url}")
    image_resp = requests.get(image_url)
    image_resp.raise_for_status()
    image_data = image_resp.content
    
    # Step 3: Upload the image binary data to LinkedIn
    print("Uploading image to LinkedIn...")
    upload_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }
    
    upload_resp = requests.post(upload_url, data=image_data, headers=upload_headers)
    upload_resp.raise_for_status()
    
    print("Image upload completed successfully!")
    return asset_urn


def post_linkedin_ugc(
    access_token: str,
    author_urn: str,
    text: str,
    visibility: str = "PUBLIC",
    image_asset_urn: Optional[str] = None
) -> dict:
    """
    Posts a user-generated content (UGC) share on LinkedIn.
    
    Args:
        access_token: OAuth2 bearer token with w_member_social scope.
        author_urn:   e.g. "urn:li:person:{id}".
        text:         The post copy.
        visibility:   "PUBLIC" or "CONNECTIONS".
        image_asset_urn: Optional—if provided, must be a valid
                         LinkedIn asset URN for an uploaded image.
    
    Returns:
        The JSON response from LinkedIn (which includes the new post's URN in `id`).
    
    Raises:
        requests.exceptions.HTTPError on non-2xx responses.
    """
    # Try UGC Posts API first
    try:
        return _post_ugc_api(access_token, author_urn, text, visibility, image_asset_urn)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("UGC API failed (403), trying legacy Share API...")
            return _post_share_api(access_token, author_urn, text, visibility)
        else:
            raise


def _post_ugc_api(access_token: str, author_urn: str, text: str, visibility: str, image_asset_urn: Optional[str]) -> dict:
    """Try the modern UGC Posts API."""
    LINKEDIN_POST_URL = "https://api.linkedin.com/v2/ugcPosts"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

    share_content = {
        "shareCommentary": {"text": text},
        "shareMediaCategory": "NONE"
    }

    if image_asset_urn:
        share_content["shareMediaCategory"] = "IMAGE"
        share_content["media"] = [
            {
                "status": "READY",
                "description": {"text": ""},
                "media": image_asset_urn
            }
        ]

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_content
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": visibility
        }
    }

    print(f"Payload being sent: {payload}")  # Debug output
    
    resp = requests.post(LINKEDIN_POST_URL, json=payload, headers=headers)
    
    # Enhanced debug output
    print(f"Response status: {resp.status_code}")
    print(f"Response headers: {dict(resp.headers)}")
    print(f"Response body: {resp.text}")
    
    resp.raise_for_status()
    return resp.json()


def _post_share_api(access_token: str, author_urn: str, text: str, visibility: str) -> dict:
    """Fallback to legacy Share API (text only)."""
    LINKEDIN_SHARE_URL = "https://api.linkedin.com/v2/shares"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

    # Convert visibility to legacy format
    visibility_mapping = {
        "PUBLIC": "anyone",
        "CONNECTIONS": "connections-only"
    }
    legacy_visibility = visibility_mapping.get(visibility, "anyone")

    payload = {
        "owner": author_urn,
        "text": {
            "text": text
        },
        "distribution": {
            "linkedInDistributionTarget": {
                "visibleToGuest": legacy_visibility == "anyone"
            }
        }
    }

    resp = requests.post(LINKEDIN_SHARE_URL, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()


def check_token_permissions(access_token: str):
    """Debug function to check what the token can access."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    # Test different endpoints to see what's accessible
    endpoints_to_test = [
        ("OpenID UserInfo", "https://api.linkedin.com/v2/userinfo"),
        ("Profile (REST)", "https://api.linkedin.com/v2/me"),
        ("Profile (Lite)", "https://api.linkedin.com/v2/people/(id={person-id})"),
    ]
    
    print("=== Token Permission Check ===")
    for name, url in endpoints_to_test:
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                print(f"✅ {name}: ACCESSIBLE")
            else:
                print(f"❌ {name}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"❌ {name}: ERROR - {str(e)}")


def main(access_token: str,
         image_url: Optional[str] = None,
         post_text: Optional[str] = None):
    """Example usage - reads access token from environment variable."""
    # Get access token securely from environment variable
    access_token = access_token
    if not access_token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN environment variable not set")
    
    # Check what the token can access
    # check_token_permissions(access_token)
    
    try:
        # Get the actual user URN
        author_urn = fetch_linkedin_urn(access_token)
        print(f"Fetched Author URN: {author_urn}")
        
        # Validate URN format
        if not author_urn.startswith('urn:li:person:'):
            raise ValueError(f"Invalid author URN format: {author_urn}")
            
        print(f"Using Author URN: {author_urn}")
        
        # Post with image
        post_text = post_text
        image_url = image_url
        
        # Upload the image first and get the asset URN
        print("Uploading image to LinkedIn...")
        if not image_url:
            asset_urn = None
        else:
            asset_urn = upload_image_to_linkedin(access_token, author_urn, image_url)
            
        # Now post with the proper asset URN
        result = post_linkedin_ugc(
            access_token=access_token,
            author_urn=author_urn,
            text=post_text,
            visibility="PUBLIC",
            image_asset_urn=asset_urn  
        )
        
        print("Published post URN:", result.get("id"))
        print("Full response:", result)
        return result
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


# if __name__ == "__main__":
#     main(access_token='A',
#         #    image_url="https://example.com/image.jpg",
#            post_text="Hello LinkedIn! This is a test post with an image.")