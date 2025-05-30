from oauth2client.client import OAuth2WebServerFlow
from googleapiclient.discovery import build
import httplib2
import os


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

import webbrowser
import http.server
import socketserver

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def connect_search_console(access_token, refresh_token, client_id, client_secret):
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    service = build('webmasters', 'v3', credentials=creds)
    return service



from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from auth.models import Integration

router = APIRouter()
from sqlalchemy.orm import Session
from auth.auth import get_db
from utils import verify_jwt_token


@router.get("/search_console/sites")
async def get_verified_sites(user_id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    user_id = user_id[1]
    try:
        user_auth = db.query(Integration).filter(Integration.user_id == user_id, Integration.provider == "GOOGLE_SEARCH_CONSOLE").first()
        if not user_auth:
            raise HTTPException(status_code=404, detail="Google Search Console account not linked")
        service = connect_search_console(
            access_token=user_auth.access_token,
            refresh_token=user_auth.refresh_token,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )

        sites = service.sites().list().execute()
        return {"sites": sites.get("siteEntry", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    
    