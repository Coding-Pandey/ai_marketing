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

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")




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
    except Exception as e:
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

