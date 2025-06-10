
from fastapi import FastAPI, HTTPException, APIRouter, Depends
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timedelta
import re
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional, Union
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from auth.models import Integration
from auth.auth import get_db
import requests
from utils import verify_jwt_token
# Load environment variables
load_dotenv()
router = APIRouter()

# Google Search Console credentials
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# OAuth scope
OAUTH_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

# Batch size for pagination
BATCH_SIZE = 5000

def refresh_google_access_token(refresh_token: str):
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    )
    data = response.json()
    if "access_token" not in data:
        raise HTTPException(status_code=401, detail=f"Failed to refresh token: {data.get('error_description', 'Unknown error')}")
    expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
    return data["access_token"], expires_at

def connect_search_console(db: Session, user_id: str):
    """Connect to Google Search Console API"""
    if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
        raise HTTPException(status_code=500, detail="Google API credentials not configured")

    # Fetch user authentication details from the database
    user_auth = db.query(Integration).filter(
        Integration.user_id == user_id,
        Integration.provider == "GOOGLE_SEARCH_CONSOLE"
    ).first()
    if not user_auth:
        raise HTTPException(status_code=404, detail="Google Search Console account not linked")

    now = datetime.utcnow()
    access_token = user_auth.access_token
    refresh_token = user_auth.refresh_token

    # Check if token is expired or close to expiring
    if not user_auth.expires_at or user_auth.expires_at < now + timedelta(seconds=60):
        if not refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token available, please re-authenticate")
        try:
            new_access_token, new_expires_at = refresh_google_access_token(refresh_token)
            user_auth.access_token = new_access_token
            user_auth.expires_at = new_expires_at
            db.commit()
            access_token = new_access_token
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Failed to refresh access token: {str(e)}")

    try:
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=[OAUTH_SCOPE]
        )
        return build('webmasters', 'v3', credentials=creds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Search Console: {str(e)}")

def fetch_all_data_paginated(service, site_url, payload_base, start_date, end_date):
    """Fetch all data with pagination"""
    payload = payload_base.copy()
    payload["startDate"] = start_date
    payload["endDate"] = end_date

    all_rows = []
    start_row = 0
    
    while True:
        payload["startRow"] = start_row
        try:
            response = service.searchanalytics().query(siteUrl=site_url, body=payload).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"API call failed: {str(e)}")

        rows = response.get("rows", [])
        if not rows:
            break

        all_rows.extend(rows)
        start_row += BATCH_SIZE
        
        if len(rows) < BATCH_SIZE:
            break

    return all_rows

def process_search_console_data(rows, branded_words=None):
    """
    Process raw API response into DataFrame
    
    Args:
        rows: Raw API response data
        branded_words: List of branded keywords (case-insensitive). If None, all keywords are marked as "Non-Branded"
    
    Returns:
        pd.DataFrame: Processed search console data
    """
    if rows is None:
        return pd.DataFrame()
    
    data = []
    
    for row in rows:
        # Handle missing or malformed row data
        if not row or "keys" not in row or len(row["keys"]) < 5:
            continue
            
        keyword = row["keys"][0]
        
        # Determine brand category
        if branded_words is None:
            brand_category = "Non-Branded"  # All keywords are non-branded when branded_words is None
        else:
            # Create pattern from branded words list
            escaped_words = [re.escape(word) for word in branded_words]
            brand_pattern = r"(?i).*(" + "|".join(escaped_words) + ").*"
            brand_category = "Branded" if re.search(brand_pattern, keyword) else "Non-Branded"
        
        data.append({
            "keyword": keyword,
            "country": row["keys"][1] if len(row["keys"]) > 1 else None,
            "device": row["keys"][2] if len(row["keys"]) > 2 else None,
            "date": row["keys"][3] if len(row["keys"]) > 3 else None,
            "page": row["keys"][4] if len(row["keys"]) > 4 else None,
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 0),
            "brand_category": brand_category
        })
    
    return pd.DataFrame(data)


def safe_divide(a, b, default=0):
    """Safe division to avoid division by zero"""
    return (a / b) if b != 0 else default

def safe_percentage(current, previous, default=0):
    """Safe percentage calculation"""
    return ((current - previous) / previous * 100) if previous != 0 else default

def format_fluctuation(value):
    """Format fluctuation with proper sign"""
    if value > 0:
        return f"+{round(value, 2)}"
    elif value < 0:
        return f"{round(value, 2)}"
    else:
        return "0"

def get_previous_period_dates(start_date_str, end_date_str):
    """Calculate previous period dates - Updated Logic"""
    # Calculate days between start and end date
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    days = (end_dt - start_dt).days + 1  # Include end date
    
    print(f"\nDate Calculation Details:")
    print(f"Current Period: {start_date_str} to {end_date_str}")
    print(f"Number of days in current period: {days}")
    
    # Calculate previous period
    prev_end_dt = start_dt - timedelta(days=1)  # Day before start_date
    prev_start_dt = prev_end_dt - timedelta(days=days-1)  # Start of previous period
    
    prev_start_date = prev_start_dt.strftime("%Y-%m-%d")
    prev_end_date = prev_end_dt.strftime("%Y-%m-%d")
    
    print(f"Previous Period: {prev_start_date} to {prev_end_date}")
    print(f"Total date range to fetch: {prev_start_date} to {end_date_str}")
    
    return prev_start_date, prev_end_date

# Pydantic models
class SearchConsoleRequest(BaseModel):
    site_url: str  # Required URL field with validation
    search_type: str = "web"  # "web", "image", "video"
    device_type: Optional[str] = "mobile"  # "mobile", "desktop", "tablet", None
    country: Optional[str] = "usa"  # ISO 3166-1 alpha-3 code like "USA", "GBR", etc.
    start_date: Optional[str] = None  # YYYY-MM-DD format, defaults to last 30 days
    end_date: Optional[str] = None    # YYYY-MM-DD format, defaults to today
    branded_words: Optional[List[str]] = None  # List of branded keywords, if None all keywords are non-branded

class KeywordMetrics(BaseModel):
    impressions: Dict[str, Any]  # {"Actual": value, "fluctuation": "+/-value"}
    clicks: Dict[str, Any]
    no_of_keywords: Dict[str, Any]
    ctr: Dict[str, Any]
    avg_position: Dict[str, Any]

class KeywordClicksEntry(BaseModel):
    keyword: str
    pos_last_30_days: int
    pos_before_30_days: int
    change: int

class KeywordImpressionsEntry(BaseModel):
    keyword: str
    pos_last_30_days: int
    pos_before_30_days: int
    change: int

class KeywordCTREntry(BaseModel):
    keyword: str
    pos_last_30_days: float
    pos_before_30_days: float
    change: float

class KeywordPositionEntry(BaseModel):
    keyword: str
    pos_last_30_days: float
    pos_before_30_days: float
    change: float

class KeywordLists(BaseModel):
    clicks: List[KeywordClicksEntry]
    impressions: List[KeywordImpressionsEntry]
    ctr: List[KeywordCTREntry]
    avg_position: List[KeywordPositionEntry]

class DailyMetrics(BaseModel):
    date: str
    branded_clicks: int
    branded_impressions: int
    branded_ctr: float
    branded_avg_position: float
    generic_clicks: int
    generic_impressions: int
    generic_ctr: float
    generic_avg_position: float

class DiffMetrics(BaseModel):
    ctr: Dict[str, float]
    position: Dict[str, float]
    click: Dict[str, float]
    impression: Dict[str, float]

class SearchConsoleResponse(BaseModel):
    # diff_metrics: DiffMetrics
    click_percentage: Dict[str, float]
    impression_percentage: Dict[str, float]
    pie_chart_data: Dict[str, Dict[str, Union[int, float]]]  # Single pie chart data structure
    branded_keywords: KeywordMetrics
    non_branded_keywords: KeywordMetrics
    branded_keyword_list: KeywordLists
    generic_keyword_list: KeywordLists
    daily_metrics: List[DailyMetrics]
