
from utils import verify_jwt_token
from auth.auth import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from auth.models import Integration, ProviderEnum
from screaming_frog.utile import GoogleSheetsService
from googleapiclient.discovery import build

router = APIRouter()

class CrawlRequest(BaseModel):
    domain: str

@router.post("/sheets/crawl")
def crawl_domain_to_sheets(
    request: CrawlRequest,
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Crawl a domain and create a Google Sheet with the results
    """
    user_id = int(user_id[1]) 
    export_tabs = ["Internal:All", "External:All", "Images:All"]
    # Get user's Google Sheets integration
    integration = db.query(Integration).filter_by(
        user_id=user_id,
        provider=ProviderEnum.GOOGLE_SHEETS
    ).first()
    
    if not integration:
        raise HTTPException(404, "Google Sheets integration not found. Please connect your Google account first.")
    
    # Check if token needs refresh
    # integration = ensure_valid_token(integration, db)
    
    # Validate domain
    domain = request.domain.strip()
    if not domain.startswith(('http://', 'https://')):
        domain = f"https://{domain}"
    
    # Create sheets service and run crawl
    sheets_service = GoogleSheetsService(integration)
    result = sheets_service.crawl_and_create_sheets(domain, export_tabs=export_tabs)

    return {
        "success": True,
        "message": f"Successfully crawled {domain} and created Google Sheet",
        "sheets": result,             
    }

@router.get("/sheets/test-connection")
def test_sheets_connection(
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Test if Google Sheets connection is working"""
    user_id = int(user_id[1]) 
    integration = db.query(Integration).filter_by(
        user_id=user_id,
        provider=ProviderEnum.GOOGLE_SHEETS
    ).first()
    
    if not integration:
        raise HTTPException(404, "Google Sheets integration not found")
    
    try:
        # integration = ensure_valid_token(integration, db)
        sheets_service = GoogleSheetsService(integration)
        
        # Try to list spreadsheets to test connection
        drive_service = build('drive', 'v3', credentials=sheets_service.credentials)
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            pageSize=1
        ).execute()
        
        return {
            "success": True,
            "message": "Google Sheets connection is working",
            "account_email": integration.user.email if hasattr(integration, 'user') else "Unknown"
        }
        
    except Exception as e:
        raise HTTPException(400, f"Google Sheets connection failed: {str(e)}")