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

    return {"message": f"{provider_name.value.capitalize()} credentials saved."}


