import os
import requests
from fastapi import FastAPI, Request, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from settings.app_intergations.app_intergations_model import OAUTH_CONFIG, ProviderEnum
# from app_intergations_model import OAUTH_CONFIG, ProviderEnum
from auth.models import Integration

from utils import verify_jwt_token, check_api_limit
from auth.auth import get_db
from typing import List

load_dotenv()

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# print(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
# print(f"GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET}")


@router.get("/login/{provider_name}")
def login(provider_name: ProviderEnum,
          token: str = Depends(verify_jwt_token)):
    cfg = OAUTH_CONFIG.get(provider_name)
    if not cfg:
        raise HTTPException(404, f"No OAuth config for {provider_name}")

    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  cfg.redirect_uri,
        "response_type": "code",
        "scope":         cfg.scopes,
        "access_type":   "offline",  
        "prompt":        "consent",
        "state":         str(token[1])
    }
    query = "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())
    return {"url": f"{cfg.auth_url}?{query}"}


@router.get("/auth/{provider_name}")
def auth_callback(
    provider_name: ProviderEnum,
    request: Request,
    state: str = None,   
    code: str = None,
    db: Session = Depends(get_db),
    # user_id: int = Depends(verify_jwt_token),
):
    if not code:
        raise HTTPException(400, "No code provided")
    print(provider_name.value)

    cfg = OAUTH_CONFIG.get(provider_name)
    if not cfg:
        raise HTTPException(404, f"No OAuth config for {provider_name}")
    
    token_resp = requests.post(
        cfg.token_url,
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": cfg.redirect_uri,
            "grant_type": "authorization_code"
        }
    )
    token_data = token_resp.json()
    print(token_data)
    if token_data.get("error"):
        raise HTTPException(400, token_data["error_description"])

    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 0))
    print(expires_at)

    # Upsert into your Integration table
    user_id = int(state)
    print(f"User ID from state: {user_id}")
    integration = (
        db.query(Integration)
          .filter_by(user_id=user_id, provider=provider_name)
          .first()
    )
    if not integration:
        integration = Integration(
            user_id       = user_id,
            provider      = provider_name,
            access_token  = token_data["access_token"],
            refresh_token = token_data.get("refresh_token"),
            expires_at    = expires_at,
            scope         = cfg.scopes
        )
        db.add(integration)
    else:
        integration.access_token  = token_data["access_token"]
        if token_data.get("refresh_token"):
            integration.refresh_token = token_data["refresh_token"]
        integration.expires_at = expires_at
        integration.scope = cfg.scopes

    db.commit()

    url = f"https://app.optiminder.com/ProfileSettingSuccess/{provider_name}"
    print(url)

    return RedirectResponse(url=url, status_code=302)


@router.get("/refresh_token/{provider_name}")
def refresh_token(provider_name: ProviderEnum, db: Session = Depends(get_db), user_id: int = Depends(verify_jwt_token)):
    user_id = user_id[1]
    integration = db.query(Integration).filter_by(user_id=user_id, provider=provider_name).first()
    if not integration or not integration.refresh_token:
        raise HTTPException(400, "No refresh token found")
    cfg = OAUTH_CONFIG.get(provider_name)
    if not cfg:
        raise HTTPException(404, f"No OAuth config for {provider_name}")
    token_resp = requests.post(cfg.token_url, data={
        "grant_type": "refresh_token",
        "refresh_token": integration.refresh_token,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET
    })
    token_data = token_resp.json()
    # print("Token Response:", token_resp.text)
    if "error" in token_data:
        raise HTTPException(
        status_code=404,
        detail="Token expired or revoked. Please reconnect your Google Search Console account."
    )
    integration.access_token = token_data["access_token"]
    
    if "refresh_token" in token_data:
        integration.refresh_token = token_data["refresh_token"]
    integration.expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 0))
    db.commit()
    return {"message": "Token refreshed successfully"}

@router.get("/app_integration_data")
async def integration_data(
    db: Session = Depends(get_db),
    user_token: tuple = Depends(verify_jwt_token),
):
    # verify_jwt_token() returns something like (sub, user_id)
    user_id = user_token[1]

    # 1. Query all Integration rows for this user in one shot
    rows: List[Integration] = (
        db.query(Integration)
          .filter(Integration.user_id == user_id)
          .all()
    )
    if rows is None:
        return []

    # 2. Build a set of all providers this user has already connected
    connected_providers = { row.provider for row in rows }

    # 3. Now loop over EVERY ProviderEnum to see if it’s in that set
    result_list = []
    for prov in ProviderEnum:
        result_list.append({
            "provider": prov.value,
            "connected": (prov in connected_providers)
        })

    # 4. Return a JSON array telling which providers are connected vs not
    return { "user_id": user_id, "integrations": result_list }



