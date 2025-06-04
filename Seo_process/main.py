from fastapi import FastAPI, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timedelta
import re
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Search Console Metrics API")

# Google Search Console credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
# ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

SITE_URL = "https://optiminder.com/"

# OAuth scope
OAUTH_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

# Batch size for pagination
BATCH_SIZE = 5000

def connect_search_console():
    """Connect to Google Search Console API"""
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, ACCESS_TOKEN]):
        raise HTTPException(status_code=500, detail="Missing Google credentials in environment variables")
    
    try:
        creds = Credentials(
            token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
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

def process_search_console_data(rows):
    """Process raw API response into DataFrame"""
    data = []
    for row in rows:
        keyword = row["keys"][0]
        brand_pattern = r"(?i).*looker.*"
        brand_category = "Branded" if re.match(brand_pattern, keyword) else "Non-Branded"
        
        data.append({
            "keyword": keyword,
            "country": row["keys"][1],
            "device": row["keys"][2],
            "date": row["keys"][3],
            "page": row["keys"][4],
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
    search_type: str = "web"  # "web", "image", "video"
    device_type: Optional[str] = "mobile"  # "mobile", "desktop", "tablet", None
    country: Optional[str] = "usa"  # ISO 3166-1 alpha-3 code like "USA", "GBR", etc.
    start_date: Optional[str] = None  # YYYY-MM-DD format, defaults to last 90 days
    end_date: Optional[str] = None    # YYYY-MM-DD format, defaults to today

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

class SearchConsoleResponse(BaseModel):
    click_percentage: Dict[str, float]
    impression_percentage: Dict[str, float]
    branded_keywords: KeywordMetrics
    non_branded_keywords: KeywordMetrics
    branded_keyword_list: KeywordLists
    generic_keyword_list: KeywordLists
    daily_metrics: List[DailyMetrics]

@app.post("/search-console-metrics", response_model=SearchConsoleResponse)
async def get_search_console_metrics(request: SearchConsoleRequest):
    """Main endpoint to get search console metrics with fluctuations"""
    try:
        # Validate input parameters
        valid_search_types = ["web", "image", "video"]
        if request.search_type not in valid_search_types:
            raise HTTPException(status_code=400, detail=f"Invalid search_type. Must be one of {valid_search_types}")
        
        valid_device_types = [None, "mobile", "desktop", "tablet"]
        if request.device_type not in valid_device_types:
            raise HTTPException(status_code=400, detail=f"Invalid device_type. Must be one of {valid_device_types[1:]} or null")
        
        # Validate and set date ranges
        if request.start_date and request.end_date:
            try:
                datetime.strptime(request.start_date, "%Y-%m-%d")
                datetime.strptime(request.end_date, "%Y-%m-%d")
                end_date = request.end_date
                start_date = request.start_date
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            # Default to last 30 days
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
        
        # Connect to Search Console
        service = connect_search_console()
        
        # Calculate previous period dates using the new logic
        prev_start_date, prev_end_date = get_previous_period_dates(start_date, end_date)

        # Build base payload with dynamic filters
        payload_base = {
            'dimensions': ['query', 'country', 'device', 'date', 'page'],
            'type': request.search_type,
            'rowLimit': BATCH_SIZE
        }
        
        # Add filters based on request
        filters = []
        if request.device_type:
            filters.append({
                'dimension': 'device',
                'expression': request.device_type.upper()
            })
        
        if request.country:
            filters.append({
                'dimension': 'country',
                'expression': request.country.upper()
            })
        
        if filters:
            payload_base['dimensionFilterGroups'] = [{'filters': filters}]

        # Fetch all data in a single call from prev_start_date to end_date
        print(f"\nAPI Call Details:")
        print(f"Fetching data for {request.search_type} search type, {request.device_type} device, {request.country} country")
        print(f"Fetching data from {prev_start_date} to {end_date}")
        
        all_rows = fetch_all_data_paginated(service, SITE_URL, payload_base, prev_start_date, end_date)
        df_all = process_search_console_data(all_rows)
        
        # Split data into current and previous periods
        df_current = df_all[(df_all['date'] >= start_date) & (df_all['date'] <= end_date)]
        df_prev = df_all[(df_all['date'] >= prev_start_date) & (df_all['date'] <= prev_end_date)]
        
        print(f"\nData Split Details:")
        print(f"Total rows fetched: {len(df_all)}")
        print(f"Current period rows: {len(df_current)}")
        print(f"Previous period rows: {len(df_prev)}")

        # Split into branded and non-branded for current period
        branded_current = df_current[df_current['brand_category'] == 'Branded']
        non_branded_current = df_current[df_current['brand_category'] == 'Non-Branded']
        branded_prev = df_prev[df_prev['brand_category'] == 'Branded']
        non_branded_prev = df_prev[df_prev['brand_category'] == 'Non-Branded']

        # Calculate percentages
        total_clicks = df_current['clicks'].sum()
        total_impressions = df_current['impressions'].sum()
        
        click_percentage = {
            "branded": safe_divide(branded_current['clicks'].sum(), total_clicks) * 100,
            "generic": safe_divide(non_branded_current['clicks'].sum(), total_clicks) * 100
        }
        
        impression_percentage = {
            "branded": safe_divide(branded_current['impressions'].sum(), total_impressions) * 100,
            "generic": safe_divide(non_branded_current['impressions'].sum(), total_impressions) * 100
        }

        # Calculate branded metrics
        branded_curr_imp = branded_current['impressions'].sum()
        branded_prev_imp = branded_prev['impressions'].sum()
        branded_curr_clicks = branded_current['clicks'].sum()
        branded_prev_clicks = branded_prev['clicks'].sum()
        branded_curr_keywords = len(branded_current['keyword'].unique())
        branded_prev_keywords = len(branded_prev['keyword'].unique())
        branded_curr_ctr = safe_divide(branded_curr_clicks, branded_curr_imp) * 100
        branded_prev_ctr = safe_divide(branded_prev_clicks, branded_prev_imp) * 100
        branded_curr_pos = branded_current['position'].mean() if len(branded_current) > 0 else 0
        branded_prev_pos = branded_prev['position'].mean() if len(branded_prev) > 0 else 0
        
        # Handle NaN values
        if pd.isna(branded_curr_pos):
            branded_curr_pos = 0
        if pd.isna(branded_prev_pos):
            branded_prev_pos = 0
            
        branded_metrics = {
            "impressions": {
                "Actual": int(branded_curr_imp),
                "fluctuation": format_fluctuation(safe_percentage(branded_curr_imp, branded_prev_imp))
            },
            "clicks": {
                "Actual": int(branded_curr_clicks),
                "fluctuation": format_fluctuation(safe_percentage(branded_curr_clicks, branded_prev_clicks))
            },
            "no_of_keywords": {
                "Actual": branded_curr_keywords,
                "fluctuation": format_fluctuation(safe_percentage(branded_curr_keywords, branded_prev_keywords))
            },
            "ctr": {
                "Actual": f"{round(branded_curr_ctr, 2)}%",
                "fluctuation": format_fluctuation(branded_curr_ctr - branded_prev_ctr)
            },
            "avg_position": {
                "Actual": round(float(branded_curr_pos), 2),
                "fluctuation": format_fluctuation(branded_curr_pos - branded_prev_pos)
            }
        }

        # Calculate non-branded metrics
        non_branded_curr_imp = non_branded_current['impressions'].sum()
        non_branded_prev_imp = non_branded_prev['impressions'].sum()
        non_branded_curr_clicks = non_branded_current['clicks'].sum()
        non_branded_prev_clicks = non_branded_prev['clicks'].sum()
        non_branded_curr_keywords = len(non_branded_current['keyword'].unique())
        non_branded_prev_keywords = len(non_branded_prev['keyword'].unique())
        non_branded_curr_ctr = safe_divide(non_branded_curr_clicks, non_branded_curr_imp) * 100
        non_branded_prev_ctr = safe_divide(non_branded_prev_clicks, non_branded_prev_imp) * 100
        non_branded_curr_pos = non_branded_current['position'].mean() if len(non_branded_current) > 0 else 0
        non_branded_prev_pos = non_branded_prev['position'].mean() if len(non_branded_prev) > 0 else 0
        
        # Handle NaN values
        if pd.isna(non_branded_curr_pos):
            non_branded_curr_pos = 0
        if pd.isna(non_branded_prev_pos):
            non_branded_prev_pos = 0
            
        non_branded_metrics = {
            "impressions": {
                "Actual": int(non_branded_curr_imp),
                "fluctuation": format_fluctuation(safe_percentage(non_branded_curr_imp, non_branded_prev_imp))
            },
            "clicks": {
                "Actual": int(non_branded_curr_clicks),
                "fluctuation": format_fluctuation(safe_percentage(non_branded_curr_clicks, non_branded_prev_clicks))
            },
            "no_of_keywords": {
                "Actual": non_branded_curr_keywords,
                "fluctuation": format_fluctuation(safe_percentage(non_branded_curr_keywords, non_branded_prev_keywords))
            },
            "ctr": {
                "Actual": f"{round(non_branded_curr_ctr, 2)}%",
                "fluctuation": format_fluctuation(non_branded_curr_ctr - non_branded_prev_ctr)
            },
            "avg_position": {
                "Actual": round(float(non_branded_curr_pos), 2),
                "fluctuation": format_fluctuation(non_branded_curr_pos - non_branded_prev_pos)
            }
        }

        # Generate keyword lists organized by metrics for branded keywords
        branded_keyword_lists = {
            "clicks": [],
            "impressions": [],
            "ctr": [],
            "avg_position": []
        }
        
        if len(df_current) > 0:
            # Aggregate by keyword for current period
            branded_current_agg = branded_current.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()
            
            # Aggregate by keyword for previous period
            branded_prev_agg = branded_prev.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()
            
            # Get all unique keywords
            all_branded_keywords = set(branded_current_agg['keyword'].tolist() + branded_prev_agg['keyword'].tolist())
            
            for keyword in all_branded_keywords:
                current_data = branded_current_agg[branded_current_agg['keyword'] == keyword]
                prev_data = branded_prev_agg[branded_prev_agg['keyword'] == keyword]
                
                # Current period metrics
                curr_pos = current_data['position'].iloc[0] if len(current_data) > 0 else 0
                curr_clicks = int(current_data['clicks'].iloc[0]) if len(current_data) > 0 else 0
                curr_impressions = int(current_data['impressions'].iloc[0]) if len(current_data) > 0 else 0
                curr_ctr = current_data['ctr'].iloc[0] if len(current_data) > 0 else 0
                
                # Previous period metrics  
                prev_pos = prev_data['position'].iloc[0] if len(prev_data) > 0 else 0
                prev_clicks = int(prev_data['clicks'].iloc[0]) if len(prev_data) > 0 else 0
                prev_impressions = int(prev_data['impressions'].iloc[0]) if len(prev_data) > 0 else 0
                prev_ctr = prev_data['ctr'].iloc[0] if len(prev_data) > 0 else 0
                
                # Handle NaN values
                if pd.isna(curr_pos): curr_pos = 0
                if pd.isna(prev_pos): prev_pos = 0
                if pd.isna(curr_ctr): curr_ctr = 0
                if pd.isna(prev_ctr): prev_ctr = 0
                
                # Add to clicks list
                branded_keyword_lists["clicks"].append(KeywordClicksEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_clicks,
                    pos_before_30_days=prev_clicks,
                    change=curr_clicks - prev_clicks
                ))
                
                # Add to impressions list
                branded_keyword_lists["impressions"].append(KeywordImpressionsEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_impressions,
                    pos_before_30_days=prev_impressions,
                    change=curr_impressions - prev_impressions
                ))
                
                # Add to CTR list
                branded_keyword_lists["ctr"].append(KeywordCTREntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_ctr * 100), 2),
                    pos_before_30_days=round(float(prev_ctr * 100), 2),
                    change=round(float((curr_ctr - prev_ctr) * 100), 2)
                ))
                
                # Add to position list
                branded_keyword_lists["avg_position"].append(KeywordPositionEntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_pos), 2),
                    pos_before_30_days=round(float(prev_pos), 2),
                    change=round(float(curr_pos - prev_pos), 2)
                ))

        # Generate keyword lists organized by metrics for generic keywords
        generic_keyword_lists = {
            "clicks": [],
            "impressions": [],
            "ctr": [],
            "avg_position": []
        }
        
        if len(df_current) > 0:
            # Aggregate by keyword for current period
            generic_current_agg = non_branded_current.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()
            
            # Aggregate by keyword for previous period
            generic_prev_agg = non_branded_prev.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()
            
            # Get all unique keywords
            all_generic_keywords = set(generic_current_agg['keyword'].tolist() + generic_prev_agg['keyword'].tolist())
            
            for keyword in all_generic_keywords:
                current_data = generic_current_agg[generic_current_agg['keyword'] == keyword]
                prev_data = generic_prev_agg[generic_prev_agg['keyword'] == keyword]
                
                # Current period metrics
                curr_pos = current_data['position'].iloc[0] if len(current_data) > 0 else 0
                curr_clicks = int(current_data['clicks'].iloc[0]) if len(current_data) > 0 else 0
                curr_impressions = int(current_data['impressions'].iloc[0]) if len(current_data) > 0 else 0
                curr_ctr = current_data['ctr'].iloc[0] if len(current_data) > 0 else 0
                
                # Previous period metrics
                prev_pos = prev_data['position'].iloc[0] if len(prev_data) > 0 else 0
                prev_clicks = int(prev_data['clicks'].iloc[0]) if len(prev_data) > 0 else 0
                prev_impressions = int(prev_data['impressions'].iloc[0]) if len(prev_data) > 0 else 0
                prev_ctr = prev_data['ctr'].iloc[0] if len(prev_data) > 0 else 0
                
                # Handle NaN values
                if pd.isna(curr_pos): curr_pos = 0
                if pd.isna(prev_pos): prev_pos = 0
                if pd.isna(curr_ctr): curr_ctr = 0
                if pd.isna(prev_ctr): prev_ctr = 0
                
                # Add to clicks list
                generic_keyword_lists["clicks"].append(KeywordClicksEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_clicks,
                    pos_before_30_days=prev_clicks,
                    change=curr_clicks - prev_clicks
                ))
                
                # Add to impressions list
                generic_keyword_lists["impressions"].append(KeywordImpressionsEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_impressions,
                    pos_before_30_days=prev_impressions,
                    change=curr_impressions - prev_impressions
                ))
                
                # Add to CTR list
                generic_keyword_lists["ctr"].append(KeywordCTREntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_ctr * 100), 2),
                    pos_before_30_days=round(float(prev_ctr * 100), 2),
                    change=round(float((curr_ctr - prev_ctr) * 100), 2)
                ))
                
                # Add to position list
                generic_keyword_lists["avg_position"].append(KeywordPositionEntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_pos), 2),
                    pos_before_30_days=round(float(prev_pos), 2),
                    change=round(float(curr_pos - prev_pos), 2)
                ))

        # Generate daily metrics for graph data
        daily_metrics = []
        if len(df_current) > 0:
            daily_data = df_current.groupby(['date', 'brand_category']).agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            # Get unique dates
            unique_dates = sorted(df_current['date'].unique())
            
            for date in unique_dates:
                date_data = daily_data[daily_data['date'] == date]
                
                # Branded metrics for this date
                branded_day = date_data[date_data['brand_category'] == 'Branded']
                branded_clicks = int(branded_day['clicks'].sum()) if len(branded_day) > 0 else 0
                branded_impressions = int(branded_day['impressions'].sum()) if len(branded_day) > 0 else 0
                branded_ctr = branded_day['ctr'].mean() if len(branded_day) > 0 else 0
                branded_pos = branded_day['position'].mean() if len(branded_day) > 0 else 0
                
                # Generic metrics for this date
                generic_day = date_data[date_data['brand_category'] == 'Non-Branded']
                generic_clicks = int(generic_day['clicks'].sum()) if len(generic_day) > 0 else 0
                generic_impressions = int(generic_day['impressions'].sum()) if len(generic_day) > 0 else 0
                generic_ctr = generic_day['ctr'].mean() if len(generic_day) > 0 else 0
                generic_pos = generic_day['position'].mean() if len(generic_day) > 0 else 0
                
                # Handle NaN values
                if pd.isna(branded_ctr): branded_ctr = 0
                if pd.isna(branded_pos): branded_pos = 0
                if pd.isna(generic_ctr): generic_ctr = 0
                if pd.isna(generic_pos): generic_pos = 0
                
                daily_metrics.append(DailyMetrics(
                    date=date,
                    branded_clicks=branded_clicks,
                    branded_impressions=branded_impressions,
                    branded_ctr=round(float(branded_ctr * 100), 2),
                    branded_avg_position=round(float(branded_pos), 2),
                    generic_clicks=generic_clicks,
                    generic_impressions=generic_impressions,
                    generic_ctr=round(float(generic_ctr * 100), 2),
                    generic_avg_position=round(float(generic_pos), 2)
                ))

        return SearchConsoleResponse(
            click_percentage=click_percentage,
            impression_percentage=impression_percentage,
            branded_keywords=KeywordMetrics(**branded_metrics),
            non_branded_keywords=KeywordMetrics(**non_branded_metrics),
            branded_keyword_list=KeywordLists(**branded_keyword_lists),
            generic_keyword_list=KeywordLists(**generic_keyword_lists),
            daily_metrics=daily_metrics
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/countries")
async def get_countries():
    """Get list of available countries with their codes"""
    try:
        import pycountry
        countries = [
            {"name": country.name, "code": country.alpha_3}
            for country in pycountry.countries
        ]
        return {"countries": countries}
    except Exception as e:
        # Fallback list of common countries
        common_countries = [
            {"name": "United States", "code": "USA"},
            {"name": "United Kingdom", "code": "GBR"},
            {"name": "Canada", "code": "CAN"},
            {"name": "Australia", "code": "AUS"},
            {"name": "Germany", "code": "DEU"},
            {"name": "France", "code": "FRA"},
            {"name": "India", "code": "IND"},
            {"name": "Japan", "code": "JPN"},
            {"name": "Brazil", "code": "BRA"},
            {"name": "Mexico", "code": "MEX"}
        ]
        return {"countries": common_countries}

@app.get("/options")
async def get_api_options():
    """Get available options for API parameters"""
    return {
        "search_types": ["web", "image", "video"],
        "device_types": ["mobile", "desktop", "tablet"],
        "date_format": "YYYY-MM-DD",
        "example_request": {
            "search_type": "web",
            "device_type": "mobile", 
            "country": "USA",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)