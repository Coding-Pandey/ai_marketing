
from utils import verify_jwt_token
from auth.auth import get_db
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from auth.models import Integration, ProviderEnum, SpreadSheet, Sf_crawl_data
from screaming_frog.utile import GoogleSheetsService
from googleapiclient.discovery import build
import uuid
from screaming_frog.model import SheetDataOut
from typing import List
from screaming_frog.seo_audit_dashboard.indexablity import indexability_kpis_and_table
from screaming_frog.seo_audit_dashboard.status_code import status_code_kpis_and_table
from screaming_frog.seo_audit_dashboard.page_title import page_title_kpis_and_table
from screaming_frog.seo_audit_dashboard.meta_description import meta_description_kpis_and_tables
from screaming_frog.seo_audit_dashboard.h_tags import h_tags_kpis_and_table
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from screaming_frog.sf_crawl import ScreamingFrogCrawlService
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
    Crawl a domain and save results directly to database
    """
    user_id = int(user_id[1])
    
    # Validate domain
    domain = request.domain.strip()
    if not domain.startswith(('http://', 'https://')):
        domain = f"https://{domain}"
    
    # Create crawl service and run crawl
    crawl_service = ScreamingFrogCrawlService(db)
    
    try:
        result = crawl_service.crawl_and_save_to_db(
            domain=domain,
            user_id=user_id,
            export_tabs=["Internal:All"]
        )
        
        return JSONResponse(
            status_code=200,
            content={
                # "success": True,
                # "message": result["message"],
                "crawl_url":domain,
                "uuid": result["uuid"]
            }
        )
        
    except Exception as e:
        raise HTTPException(500, f"Crawl failed: {str(e)}")    

@router.get("/crawl_data_info")
def crawled_id_fetch(
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):

    """
    Get user's crawl history
    """
    user_id = int(user_id[1])
    
    records = (
        db.query(Sf_crawl_data)
        .filter_by(user_id=user_id)
        .order_by(Sf_crawl_data.datatime.desc())
        .all()
    )
    
    crawl_history = []
    for record in records:
        crawl_history.append({
            "uuid": record.uuid,
            "crawl_url": record.crawl_url,
            "selected_site": record.is_seleted
        })
    
    return JSONResponse(
        status_code=200,
        content={
            "crawl_history": crawl_history
        }
    )
    

@router.get("/crawl_data/{uuid}")
def fetch_crawl_data(
    uuid: str,
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Fetch crawl data from database by UUID
    """
    user_id = int(user_id[1])
    
    # Get crawl data from database
    record = (
        db.query(Sf_crawl_data)
        .filter_by(uuid=uuid, user_id=user_id)
        .first()
    )
    
    if not record:
        raise HTTPException(404, f"No crawl data found for UUID {uuid}")
    
    # Return the stored dashboard data
    return JSONResponse(
        status_code=200,
        content=record.crawl_json_data
    )



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
    
    

    

