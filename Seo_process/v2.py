from oauth2client.client import OAuth2WebServerFlow
from googleapiclient.discovery import build
import httplib2
import os
import pandas as pd
from Seo_process.seo_models import SiteData
from datetime import datetime, timedelta
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from auth.models import Integration
from Seo_process.utile import SearchConsoleService, DataProcessor
from Seo_process.ranking_keyword import RankingKeywordsAnalyzer, SEOMetricsCalculator
router = APIRouter()
from sqlalchemy.orm import Session
from auth.auth import get_db
from utils import verify_jwt_token
import webbrowser
import http.server
import socketserver
from Seo_process.branded_keywords_analysis import (
    BATCH_SIZE, DailyMetrics, KeywordCTREntry, KeywordClicksEntry,
    KeywordImpressionsEntry, KeywordLists, KeywordMetrics, KeywordPositionEntry,
    SearchConsoleRequest, SearchConsoleResponse, fetch_all_data_paginated,
    format_fluctuation, get_previous_period_dates, process_search_console_data,
    safe_divide, safe_percentage
)
import requests
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

def refresh_google_access_token(refresh_token: str):
    """Refresh Google OAuth access token"""
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



def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj



# get_site_data = SearchConsoleService.get_site_data

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
    except RefreshError:
        # Handle case where refresh token is invalid
        raise HTTPException(
            status_code=401,
            detail="Refresh token is invalid. Please re-link your Google Search Console account."
        )
    except Exception as e:
        # Handle other unexpected errors
        raise HTTPException(status_code=500, detail=str(e))

    
    
@router.post("/search_console/")
async def get_search_console_data(
    data: SiteData,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Fetch and analyze Google Search Console data for a given site and date range.
    
    Returns comparison metrics, line plot data, and keyword ranking distribution.
    """
    try:
        user_id = user_id[1]
        # Validate date range
        start_dt = datetime.strptime(data.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(data.end_date, "%Y-%m-%d")
        
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        date_diff = (end_dt - start_dt).days
        
        # Calculate extended date range for comparison
        doubled_days = date_diff * 2
        new_start_date = (start_dt - timedelta(days=doubled_days)).strftime("%Y-%m-%d")
        
        print(f"Original range: {data.start_date} to {data.end_date}")
        print(f"Extended range: {new_start_date} to {data.end_date}")

        user_auth = db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.provider == "GOOGLE_SEARCH_CONSOLE"
        ).first()
        if not user_auth:
            raise HTTPException(status_code=404, detail="Google Search Console account not linked")
        
        # Initialize Search Console service
        # Note: You'll need to provide these credentials
        search_console = SearchConsoleService(
            access_token=user_auth.access_token,
            refresh_token=user_auth.refresh_token,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        # Fetch data
        raw_data = search_console.get_site_data(
            site_url=data.site_url,
            device=data.device_type,
            country=data.country,
            search_type=data.search_type,
            start_date=new_start_date,
            end_date=data.end_date
        )
        
        if not raw_data:
            raise HTTPException(status_code=404, detail="No data found for the specified site")
        
        # Process data
        df = DataProcessor.structure_dataframe(raw_data)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data available after processing")
        
        print(f"Processed {len(df)} records")
        
        # Generate comparison matrix
        card_matrix = DataProcessor.create_comparison_matrix(df)
        card_matrix = convert_numpy_types(card_matrix)
        
        # Generate device performance comparison
        device_performance = DataProcessor.create_device_performance_comparison(
            df, data.start_date, data.end_date
        )
        device_performance = convert_numpy_types(device_performance)
        
        # Generate device distribution data
        device_distribution = DataProcessor.create_device_distribution_data(
            df, data.start_date, data.end_date
        )
        device_distribution = convert_numpy_types(device_distribution)
        
        # Prepare line plot data
        line_plot1, line_plot2 = DataProcessor.prepare_line_plot_data(df)
        
        # Calculate keyword ranking distribution
        df['rank_group'] = df['position'].apply(DataProcessor.classify_rank)
        rank_counts = df.groupby(['date', 'rank_group']).size().unstack(fill_value=0).sort_index()
        
        # Ensure all rank groups are present
        for col in ['Top 3', 'Top 10', 'Top 20+']:
            if col not in rank_counts.columns:
                rank_counts[col] = 0
        
        rank_counts = rank_counts[['Top 3', 'Top 10', 'Top 20+']]
        
        # Prepare response
        response_data = {
            "card_matrix": card_matrix,
            "device_performance": device_performance,
            "device_distribution": device_distribution,
            "line_plot_data": {
                "period1": line_plot1.reset_index().to_dict('records'),
                "period2": line_plot2.reset_index().to_dict('records')
            },
            "keywords_ranking": rank_counts.reset_index().to_dict('records'),
            "summary": {
                "total_records": len(df),
                "date_range": f"{new_start_date} to {data.end_date}",
                "current_period": f"{data.start_date} to {data.end_date}",
                "unique_queries": df['query'].nunique() if 'query' in df.columns else 0,
                "unique_pages": df['page'].nunique() if 'page' in df.columns else 0,
                "devices_analyzed": df['device'].nunique() if 'device' in df.columns else 0
            }
        }
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/ranking_keywords/")
async def get_ranking_keywords_analysis(data: SiteData,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)):
    """
    Analyze ranking keywords data with comprehensive metrics.
    
    Returns:
        - Bucket matrix with ranking distribution
        - Daily time series with all metrics  
        - Improved/declined keywords
        - Summary statistics
    """
    try:
        user_id = user_id[1]
        user_auth = db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.provider == "GOOGLE_SEARCH_CONSOLE"
        ).first()
        if not user_auth:
            raise HTTPException(status_code=404, detail="Google Search Console account not linked")
        # Initialize the analyzer
        analyzer = RankingKeywordsAnalyzer()

        search_console = SearchConsoleService(
            access_token=user_auth.access_token,
            refresh_token=user_auth.refresh_token,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        
        # Perform complete analysis
        result = analyzer.analyze_keywords(
            site_url=data.site_url,
            device_type=data.device_type,
            country=data.country,
            search_type=data.search_type,
            start_date=data.start_date,
            end_date=data.end_date,
            get_site_data_func=search_console.get_site_data
        )
        
        # Optional: Add additional SEO metrics
        # if analyzer.df_current is not None and not analyzer.df_current.empty:
        #     # Calculate visibility score
        #     visibility_score = SEOMetricsCalculator.calculate_visibility_score(analyzer.df_current)
        #     result['visibility_score'] = visibility_score
            
        #     # Detect keyword cannibalization
        #     cannibalization_issues = SEOMetricsCalculator.detect_keyword_cannibalization(analyzer.df_current)
        #     result['cannibalization_issues'] = cannibalization_issues
        

        print(result)
        return result
        
    except Exception as e:
        print(f"Error in ranking keywords analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/branded_word_analysis", response_model=SearchConsoleResponse)
async def get_search_console_metrics(
    request: SearchConsoleRequest,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Get search console metrics with fluctuations"""
    try:
        try:
            user_id = user_id[1]
        except (IndexError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid JWT token structure")

        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google API credentials not configured")

        user_auth = db.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.provider == "GOOGLE_SEARCH_CONSOLE"
        ).first()
        if not user_auth:
            raise HTTPException(status_code=404, detail="Google Search Console account not linked")

        now = datetime.utcnow()
        if not user_auth.expires_at or user_auth.expires_at < now + timedelta(seconds=60):
            if not user_auth.refresh_token:
                raise HTTPException(status_code=401, detail="No refresh token available, please re-authenticate")
            try:
                new_access_token, new_expires_at = refresh_google_access_token(user_auth.refresh_token)
                user_auth.access_token = new_access_token
                user_auth.expires_at = new_expires_at
                db.commit()
            except Exception as e:
                raise HTTPException(status_code=401, detail=f"Failed to refresh access token: {str(e)}")

        valid_search_types = ["web", "image", "video"]
        if request.search_type not in valid_search_types:
            raise HTTPException(status_code=400, detail=f"Invalid search_type. Must be one of {valid_search_types}")

        valid_device_types = [None, "mobile", "desktop", "tablet"]
        if request.device_type not in valid_device_types:
            raise HTTPException(status_code=400, detail=f"Invalid device_type. Must be one of {valid_device_types[1:]} or null")

        if request.start_date and request.end_date:
            try:
                datetime.strptime(request.start_date, "%Y-%m-%d")
                datetime.strptime(request.end_date, "%Y-%m-%d")
                end_date = request.end_date
                start_date = request.start_date
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")

        service = connect_search_console(
            access_token=user_auth.access_token,
            refresh_token=user_auth.refresh_token,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )

        prev_start_date, prev_end_date = get_previous_period_dates(start_date, end_date)

        payload_base = {
            'dimensions': ['query', 'country', 'device', 'date', 'page'],
            'type': request.search_type,
            'rowLimit': BATCH_SIZE
        }

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

        print(f"\nAPI Call Details:")
        print(f"Fetching data for {request.search_type} search type, {request.device_type} device, {request.country} country")
        print(f"Fetching data for site: {request.site_url}")
        print(f"Fetching data from {prev_start_date} to {end_date}")

        all_rows = fetch_all_data_paginated(service, str(request.site_url), payload_base, prev_start_date, end_date)
        df_all = process_search_console_data(all_rows)

        df_current = df_all[(df_all['date'] >= start_date) & (df_all['date'] <= end_date)]
        df_prev = df_all[(df_all['date'] >= prev_start_date) & (df_all['date'] <= prev_end_date)]

        print(f"\nData Split Details:")
        print(f"Total rows fetched: {len(df_all)}")
        print(f"Current period rows: {len(df_current)}")
        print(f"Previous period rows: {len(df_prev)}")

        branded_current = df_current[df_current['brand_category'] == 'Branded']
        non_branded_current = df_current[df_current['brand_category'] == 'Non-Branded']
        branded_prev = df_prev[df_prev['brand_category'] == 'Branded']
        non_branded_prev = df_prev[df_prev['brand_category'] == 'Non-Branded']

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

        branded_keyword_lists = {
            "clicks": [],
            "impressions": [],
            "ctr": [],
            "avg_position": []
        }

        if len(df_current) > 0:
            branded_current_agg = branded_current.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()

            branded_prev_agg = branded_prev.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()

            all_branded_keywords = set(branded_current_agg['keyword'].tolist() + branded_prev_agg['keyword'].tolist())

            for keyword in all_branded_keywords:
                current_data = branded_current_agg[branded_current_agg['keyword'] == keyword]
                prev_data = branded_prev_agg[branded_prev_agg['keyword'] == keyword]

                curr_pos = current_data['position'].iloc[0] if len(current_data) > 0 else 0
                curr_clicks = int(current_data['clicks'].iloc[0]) if len(current_data) > 0 else 0
                curr_impressions = int(current_data['impressions'].iloc[0]) if len(current_data) > 0 else 0
                curr_ctr = current_data['ctr'].iloc[0] if len(current_data) > 0 else 0

                prev_pos = prev_data['position'].iloc[0] if len(prev_data) > 0 else 0
                prev_clicks = int(prev_data['clicks'].iloc[0]) if len(prev_data) > 0 else 0
                prev_impressions = int(prev_data['impressions'].iloc[0]) if len(current_data) > 0 else 0
                prev_ctr = prev_data['ctr'].iloc[0] if len(prev_data) > 0 else 0

                if pd.isna(curr_pos): curr_pos = 0
                if pd.isna(prev_pos): prev_pos = 0
                if pd.isna(curr_ctr): curr_ctr = 0
                if pd.isna(prev_ctr): prev_ctr = 0

                branded_keyword_lists["clicks"].append(KeywordClicksEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_clicks,
                    pos_before_30_days=prev_clicks,
                    change=curr_clicks - prev_clicks
                ))

                branded_keyword_lists["impressions"].append(KeywordImpressionsEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_impressions,
                    pos_before_30_days=prev_impressions,
                    change=curr_impressions - prev_impressions
                ))

                branded_keyword_lists["ctr"].append(KeywordCTREntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_ctr * 100), 2),
                    pos_before_30_days=round(float(prev_ctr * 100), 2),
                    change=round(float((curr_ctr - prev_ctr) * 100), 2)
                ))

                branded_keyword_lists["avg_position"].append(KeywordPositionEntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_pos), 2),
                    pos_before_30_days=round(float(prev_pos), 2),
                    change=round(float(curr_pos - prev_pos), 2)
                ))

        generic_keyword_lists = {
            "clicks": [],
            "impressions": [],
            "ctr": [],
            "avg_position": []
        }

        if len(df_current) > 0:
            generic_current_agg = non_branded_current.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()

            generic_prev_agg = non_branded_prev.groupby('keyword').agg({
                'position': 'mean',
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean'
            }).reset_index()

            all_generic_keywords = set(generic_current_agg['keyword'].tolist() + generic_prev_agg['keyword'].tolist())

            for keyword in all_generic_keywords:
                current_data = generic_current_agg[generic_current_agg['keyword'] == keyword]
                prev_data = generic_prev_agg[generic_prev_agg['keyword'] == keyword]

                curr_pos = current_data['position'].iloc[0] if len(current_data) > 0 else 0
                curr_clicks = int(current_data['clicks'].iloc[0]) if len(current_data) > 0 else 0
                curr_impressions = int(current_data['impressions'].iloc[0]) if len(current_data) > 0 else 0
                curr_ctr = current_data['ctr'].iloc[0] if len(current_data) > 0 else 0

                prev_pos = prev_data['position'].iloc[0] if len(prev_data) > 0 else 0
                prev_clicks = int(prev_data['clicks'].iloc[0]) if len(prev_data) > 0 else 0
                prev_impressions = int(prev_data['impressions'].iloc[0]) if len(prev_data) > 0 else 0
                prev_ctr = prev_data['ctr'].iloc[0] if len(prev_data) > 0 else 0

                if pd.isna(curr_pos): curr_pos = 0
                if pd.isna(prev_pos): prev_pos = 0
                if pd.isna(curr_ctr): curr_ctr = 0
                if pd.isna(prev_ctr): prev_ctr = 0

                generic_keyword_lists["clicks"].append(KeywordClicksEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_clicks,
                    pos_before_30_days=prev_clicks,
                    change=curr_clicks - prev_clicks
                ))

                generic_keyword_lists["impressions"].append(KeywordImpressionsEntry(
                    keyword=keyword,
                    pos_last_30_days=curr_impressions,
                    pos_before_30_days=prev_impressions,
                    change=curr_impressions - prev_impressions
                ))

                generic_keyword_lists["ctr"].append(KeywordCTREntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_ctr * 100), 2),
                    pos_before_30_days=round(float(prev_ctr * 100), 2),
                    change=round(float((curr_ctr - prev_ctr) * 100), 2)
                ))

                generic_keyword_lists["avg_position"].append(KeywordPositionEntry(
                    keyword=keyword,
                    pos_last_30_days=round(float(curr_pos), 2),
                    pos_before_30_days=round(float(prev_pos), 2),
                    change=round(float(curr_pos - prev_pos), 2)
                ))

        daily_metrics = []
        if len(df_current) > 0:
            daily_data = df_current.groupby(['date', 'brand_category']).agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()

            unique_dates = sorted(df_current['date'].unique())

            for date in unique_dates:
                date_data = daily_data[daily_data['date'] == date]

                branded_day = date_data[date_data['brand_category'] == 'Branded']
                branded_clicks = int(branded_day['clicks'].sum()) if len(branded_day) > 0 else 0
                branded_impressions = int(branded_day['impressions'].sum()) if len(branded_day) > 0 else 0
                branded_ctr = branded_day['ctr'].mean() if len(branded_day) > 0 else 0
                branded_pos = branded_day['position'].mean() if len(branded_day) > 0 else 0

                generic_day = date_data[date_data['brand_category'] == 'Non-Branded']
                generic_clicks = int(generic_day['clicks'].sum()) if len(generic_day) > 0 else 0
                generic_impressions = int(generic_day['impressions'].sum()) if len(generic_day) > 0 else 0
                generic_ctr = generic_day['ctr'].mean() if len(generic_day) > 0 else 0
                generic_pos = generic_day['position'].mean() if len(generic_day) > 0 else 0

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



@router.get("/report_filter")
async def get_countries():
    """Get list of available countries with their codes"""
    try:
        import pycountry
        search_types= ["web", "image", "video"],
        device_types= ["mobile", "desktop", "tablet"]
        countries = [
            {"name": country.name, "code": country.alpha_3}
            for country in pycountry.countries
        ]
        return {"countries": countries,
                "search_types": search_types,
        "device_types":device_types }
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
        return {"countries": common_countries,
                "search_types": search_types,
        "device_types":device_types }
    
    