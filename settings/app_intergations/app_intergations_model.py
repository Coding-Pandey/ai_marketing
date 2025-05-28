from enum import Enum as PyEnum
from pydantic import BaseModel
from typing import Dict


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


class OAuthConfig(BaseModel):
    auth_url:     str
    token_url:    str
    scopes:       str
    redirect_uri: str


OAUTH_CONFIG: Dict[ProviderEnum, OAuthConfig] = {
    ProviderEnum.GOOGLE_SEARCH_CONSOLE: OAuthConfig(
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        scopes       = "openid email profile https://www.googleapis.com/auth/webmasters.readonly",
        redirect_uri = "https://api.optiminder.com/api/auth/google_search_console"
    ),

    ProviderEnum.GOOGLE_ANALYTICS: OAuthConfig(
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        scopes       = "openid email profile https://www.googleapis.com/auth/analytics.readonly",
        redirect_uri = "https://yourapp.com/auth/google"
    ),

    ProviderEnum.GOOGLE_CHROME_UX_REPORT: OAuthConfig(
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        # scopes       = "openid email profile https://www.googleapis.com/auth/chromeuxreport",
        scopes = "https://www.googleapis.com/auth/chromeuxreport",
        redirect_uri = "https://yourapp.com/auth/google"
    ),

    ProviderEnum.GOOGLE_ADS: OAuthConfig(
        auth_url     = "https://accounts.google.com/o/oauth2/v2/auth",
        token_url    = "https://oauth2.googleapis.com/token",
        scopes       = "openid email profile https://www.googleapis.com/auth/adsense.readonly",
        redirect_uri = "https://yourapp.com/auth/google"
    ),

    ProviderEnum.FACEBOOK: OAuthConfig(
        auth_url     = "https://www.facebook.com/v11.0/dialog/oauth",
        token_url    = "https://graph.facebook.com/v11.0/oauth/access_token",
        scopes       = "email public_profile",
        redirect_uri = "https://yourapp.com/auth/facebook"
    ),

    ProviderEnum.LINKEDIN: OAuthConfig(
        auth_url     = "https://www.linkedin.com/oauth/v2/authorization",
        token_url    = "https://www.linkedin.com/oauth/v2/accessToken",
        scopes       = "r_emailaddress r_liteprofile",
        redirect_uri = "https://yourapp.com/auth/linkedin"
    ),

    ProviderEnum.TWITTER: OAuthConfig(
        auth_url     = "https://twitter.com/i/oauth2/authorize",
        token_url    = "https://api.twitter.com/2/oauth2/token",
        scopes       = "tweet.read users.read offline.access",
        redirect_uri = "https://yourapp.com/auth/twitter"
    ),

    ProviderEnum.INSTAGRAM: OAuthConfig(
        auth_url     = "https://api.instagram.com/oauth/authorize",
        token_url    = "https://api.instagram.com/oauth/access_token",
        scopes       = "user_profile,user_media",
        redirect_uri = "https://yourapp.com/auth/instagram"
    ),

    ProviderEnum.TIKTOK: OAuthConfig(
        auth_url     = "https://www.tiktok.com/auth/authorize",
        token_url    = "https://open-api.tiktok.com/oauth/access_token/",
        scopes       = "user.info.basic",
        redirect_uri = "https://yourapp.com/auth/tiktok"
    ),
}