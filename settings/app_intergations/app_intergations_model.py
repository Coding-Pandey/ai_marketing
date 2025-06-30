from enum import Enum as PyEnum
from pydantic import BaseModel
from typing import Dict, Optional
from pydantic import BaseModel
import os


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")



class ProviderEnum(PyEnum):
    # GOOGLE     = "google"
    GOOGLE_SEARCH_CONSOLE  = "google_search_console"
    GOOGLE_ANALYTICS       = "google_analytics"
    GOOGLE_ADS             = "google_ads"
    GOOGLE_CHROME_UX_REPORT = "google_chrome_ux_report"
    FACEBOOK   = "facebook"
    LINKEDIN   = "linkedin"
    TWITTER    = "twitter"
    INSTAGRAM  = "instagram"
    TIKTOK     = "tiktok"
    GOOGLE_SHEETS = "google_sheets"


class OAuthConfig(BaseModel):
    client_id:          str 
    client_secret:      str 
    auth_url:     str
    token_url:    str
    scopes:       str
    redirect_uri: str
    extra_auth_params:   Optional[Dict[str, str]] = None  


OAUTH_CONFIG: Dict[ProviderEnum, OAuthConfig] = {
    ProviderEnum.GOOGLE_SEARCH_CONSOLE: OAuthConfig(
        client_id          = GOOGLE_CLIENT_ID,
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        scopes       = "openid email profile https://www.googleapis.com/auth/webmasters.readonly",
        redirect_uri = "https://api.optiminder.com/api/auth/google_search_console",
        client_secret = GOOGLE_CLIENT_SECRET,
        extra_auth_params  = {
            "access_type": "offline",
            "prompt":      "consent"
        }
    ),

    ProviderEnum.GOOGLE_ANALYTICS: OAuthConfig(
        client_id     = "",
        client_secret = "",
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        scopes       = "openid email profile https://www.googleapis.com/auth/analytics.readonly",
        redirect_uri = "https://yourapp.com/auth/google"
    ),

    ProviderEnum.GOOGLE_CHROME_UX_REPORT: OAuthConfig(
        client_id     = "",
        client_secret = "",
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        # scopes       = "openid email profile https://www.googleapis.com/auth/chromeuxreport",
        scopes = "https://www.googleapis.com/auth/chromeuxreport",
        redirect_uri = "https://yourapp.com/auth/google"
    ),

    ProviderEnum.GOOGLE_ADS: OAuthConfig(
        client_id     = "",
        client_secret = "",
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        scopes       = "openid email profile https://www.googleapis.com/auth/adsense.readonly",
        redirect_uri = "https://yourapp.com/auth/google"
    ),

    ProviderEnum.FACEBOOK: OAuthConfig(
        client_id     = "",
        client_secret = "",
        auth_url     = "https://www.facebook.com/v11.0/dialog/oauth",
        token_url    = "https://graph.facebook.com/v11.0/oauth/access_token",
        scopes       = "email public_profile",
        redirect_uri = "https://yourapp.com/auth/facebook"
    ),

    ProviderEnum.LINKEDIN: OAuthConfig(
        client_id     = LINKEDIN_CLIENT_ID,
        client_secret = LINKEDIN_CLIENT_SECRET,
        auth_url     = "https://www.linkedin.com/oauth/v2/authorization",
        token_url    = "https://www.linkedin.com/oauth/v2/accessToken",
        scopes       = "openid profile email w_member_social",#"r_liteprofile r_emailaddress w_member_social",#,"r_emailaddress r_liteprofile",
        redirect_uri = "https://api.optiminder.com/api/auth/linkedin",
        # redirect_uri = "http://127.0.0.1:8000/auth/linkedin",
        extra_auth_params  = {
            "access_type": "offline",
            "prompt":      "consent"
        }
    ),

    ProviderEnum.TWITTER: OAuthConfig(
        client_id     = "",
        client_secret = "",
        auth_url     = "https://twitter.com/i/oauth2/authorize",
        token_url    = "https://api.twitter.com/2/oauth2/token",
        scopes       = "tweet.read users.read offline.access",
        redirect_uri = "https://yourapp.com/auth/twitter"
    ),

    ProviderEnum.INSTAGRAM: OAuthConfig(
        client_id     = "",
        client_secret = "",
        auth_url     = "https://api.instagram.com/oauth/authorize",
        token_url    = "https://api.instagram.com/oauth/access_token",
        scopes       = "user_profile,user_media",
        redirect_uri = "https://yourapp.com/auth/instagram"
    ),

    ProviderEnum.TIKTOK: OAuthConfig(
        client_id     = "",
        client_secret = "",
        auth_url     = "https://www.tiktok.com/auth/authorize",
        token_url    = "https://open-api.tiktok.com/oauth/access_token/",
        scopes       = "user.info.basic",
        redirect_uri = "https://yourapp.com/auth/tiktok"
    ),  
    
    ProviderEnum.GOOGLE_SHEETS : OAuthConfig(
    client_id     = GOOGLE_CLIENT_ID,
    client_secret = GOOGLE_CLIENT_SECRET,
    auth_url      = "https://accounts.google.com/o/oauth2/v2/auth",
    token_url     = "https://oauth2.googleapis.com/token",
    scopes        = "https://www.googleapis.com/auth/spreadsheets",
    redirect_uri  = "http://127.0.0.1:8000/auth/google_sheets",
    extra_auth_params = {
        "access_type": "offline",
        "prompt":      "consent"
    }
)
}