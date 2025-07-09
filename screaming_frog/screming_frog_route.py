
from utils import verify_jwt_token
from auth.auth import get_db
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from auth.models import Integration, ProviderEnum, SpreadSheet
from screaming_frog.utile import GoogleSheetsService
from googleapiclient.discovery import build
import uuid
from screaming_frog.model import SheetDataOut
from typing import List
from screaming_frog.seo_audit_dashboard.indexablity import indexability_kpis_and_table
from screaming_frog.seo_audit_dashboard.status_code import status_code_kpis_and_table
from screaming_frog.seo_audit_dashboard.page_title import page_title_kpis_and_table
from screaming_frog.seo_audit_dashboard.meta_description import meta_description_kpis_and_tables
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
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
    batch_uuid = uuid.uuid4().hex
    sheets_info = sheets_service.crawl_and_create_sheets(
        domain,
        export_tabs=export_tabs
    )
    
    for info in sheets_info:
        record = SpreadSheet(
            uuid=batch_uuid,
            user_id=user_id,
            spreadsheet_id=info["domainspreadsheet_id"],
            spreadsheet_name=info["tab"],
            spreadsheet_url=info["spreadsheet_url"],
            crawl_url = domain
        )
        db.add(record)
    db.commit()
    

    return {
        "success": True,
        "message": f"Successfully crawled {domain} and created {len(sheets_info)} sheets",
        "batch_uuid": batch_uuid,
        "sheets": sheets_info
    }

@router.get("/crawl_data_info")
def crawled_id_fetch(
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Return all distinct crawl batches (uuid + crawl_url) for this user.
    """
    user_id = int(user_id[1])

    # Query for distinct (uuid, crawl_url) pairs
    rows = (
        db
        .query(SpreadSheet.uuid, SpreadSheet.crawl_url)
        .filter(SpreadSheet.user_id == user_id)
        .distinct()
        .all()
    )

    if not rows:
        return []

    # Build a list of dicts
    result = [
        {"uuid": uuid, "crawl_url": crawl_url}
        for uuid, crawl_url in rows
    ]

    return result
    
    

@router.get("/crawl_data/{uuid}")
def fetch_spreadsheet_data(
    uuid: str,
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Fetch the single-tab data ("Sheet1") for all spreadsheets 
    saved under the same crawl-batch UUID.
    """
    user_id = int(user_id[1])

    # Ensure user has Google Sheets connected
    integration = (
        db.query(Integration)
          .filter_by(user_id=user_id, provider=ProviderEnum.GOOGLE_SHEETS)
          .first()
    )
    if not integration:
        raise HTTPException(404, "Google Sheets integration not found.")

    # Lookup all spreadsheets for this batch
    records = (
        db.query(SpreadSheet)
          .filter_by(uuid=uuid, user_id=user_id)
          .all()
    )
    if not records:
        raise HTTPException(404, f"No spreadsheets found for UUID {uuid}")

    sheets_svc = GoogleSheetsService(integration)
    sheets_data = []  # will hold plain dicts: {"tab": ..., "values": [ {col: cell, ...}, ... ]}

    for record in records:
        try:
            raw: List[List[Optional[str]]] = sheets_svc.get_sheet_values(
                record.spreadsheet_id, "Sheet1"
            )
        except Exception as e:
            raise HTTPException(400, f"Error reading Sheet1 from {record.spreadsheet_id}: {e}")

        if not raw or len(raw) < 2:
            continue

        header, *rows = raw
        # convert each row into a dict keyed by header
        dict_rows = [
            { header[i]: cell for i, cell in enumerate(row) }
            for row in rows
        ]

        sheets_data.append({
            "tab": record.spreadsheet_name,
            "values": dict_rows
        })

    # now find the tab we care about and compute KPIs
    try:
        # find first sheet with tab == "Internal:All"
        sheet = next((s for s in sheets_data if s["tab"] == "Internal:All"), None)
        if not sheet:
            raise HTTPException(400, "No 'Internal:All' tab found")

        dashboard = {
            "indexability": indexability_kpis_and_table(sheet)
            # "status_code": status_code_kpis_and_table(sheet),
            # "page_title":page_title_kpis_and_table(sheet),
            # "meta_description": meta_description_kpis_and_tables(sheet)
        }

    except HTTPException:
        # re‑raise FastAPI HTTPExceptions untouched
        raise
    except Exception as e:
        raise HTTPException(400, f"error in KPI calculation: {e}")

    return JSONResponse(status_code=200, content=dashboard)


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
    
    
    