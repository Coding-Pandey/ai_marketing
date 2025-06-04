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


REFRESH_TOKEN = ""
ACCESS_TOKEN = ""



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
    # user_id: str = Depends(verify_jwt_token),
    # db: Session = Depends(get_db)
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
        
        # Initialize Search Console service
        # Note: You'll need to provide these credentials
        search_console = SearchConsoleService(
            access_token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
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



# @router.post("/ranking_keywords/")
# async def verify_site(data: SiteData):
    try:
        # Parse dates and calculate periods
        start_dt = datetime.strptime(data.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(data.end_date, "%Y-%m-%d")
        n_days = (end_dt - start_dt).days + 1

        # Calculate previous period (same duration, ending day before current period starts)
        prev_end_dt = start_dt - timedelta(days=1)
        prev_start_dt = prev_end_dt - timedelta(days=n_days - 1)

        print(f"Current Period: {data.start_date} to {data.end_date}")
        print(f"Previous Period: {prev_start_dt.strftime('%Y-%m-%d')} to {prev_end_dt.strftime('%Y-%m-%d')}")

        # Fetch data for both periods
        raw_data = get_site_data(
            site_url=data.site_url,
            device=data.device_type,
            country=data.country,
            type=data.search_type,
            start_date=prev_start_dt.strftime("%Y-%m-%d"),
            end_date=end_dt.strftime("%Y-%m-%d")
        )

        if not raw_data:
            raise HTTPException(status_code=404, detail="No data found for the specified site")
        
        # Structure the dataframe
        df = structure_dataframe(raw_data)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found for the specified site")
        
        # Ensure Date column is datetime
        if 'Date' not in df.columns:
            # If Date column doesn't exist, try to create it from the data structure
            if 'date' in df.columns:
                df['Date'] = pd.to_datetime(df['date'])
            else:
                raise ValueError("Date column not found in dataframe")
        else:
            df['Date'] = pd.to_datetime(df['Date'])

        # Define ranking buckets
        def classify_bucket(pos: float) -> str:
            if pd.isna(pos):
                return "Pos 21+"
            if pos <= 3:
                return "Top 3"
            elif pos <= 10:
                return "Top 4–10" 
            elif pos <= 20:
                return "Top 11–20"
            else:
                return "Pos 21+"
        
        df['rank_bucket'] = df['position'].apply(classify_bucket)

        # Split into current vs previous periods
        mask_cur = (df['Date'] >= start_dt) & (df['Date'] <= end_dt)
        mask_prv = (df['Date'] >= prev_start_dt) & (df['Date'] <= prev_end_dt)

        df_current = df.loc[mask_cur].copy()
        df_prev = df.loc[mask_prv].copy()

        # 1. BUCKET MATRIX - Count unique keywords in each ranking bucket
        all_buckets = ["Top 3", "Top 4–10", "Top 11–20", "Pos 21+"]
        
        # Get unique keywords per bucket for current period
        cur_counts = (
            df_current.groupby('rank_bucket')['query']
            .nunique()
            .reindex(all_buckets, fill_value=0)
        )
        
        # Get unique keywords per bucket for previous period  
        prev_counts = (
            df_prev.groupby('rank_bucket')['query']
            .nunique()
            .reindex(all_buckets, fill_value=0)
        )

        bucket_matrix = pd.DataFrame({
            'rank_bucket': all_buckets,
            'current_count': cur_counts.values,
            'previous_count': prev_counts.values
        })
        
        bucket_matrix['delta_abs'] = bucket_matrix['current_count'] - bucket_matrix['previous_count']
        
        # Calculate percentage change (handle division by zero)
        bucket_matrix['delta_pct'] = bucket_matrix.apply(
            lambda row: (
                (row['current_count'] - row['previous_count']) / row['previous_count'] * 100
                if row['previous_count'] > 0 
                else (100 if row['current_count'] > 0 else 0)
            ), axis=1
        ).round(1)

        # 2. DAILY TIME SERIES - For stacked area chart with multiple metrics
        
        # Prepare aggregation functions for different metrics
        agg_functions = {
            'query': 'nunique',  # Unique keywords count
            'clicks': 'sum',     # Total clicks
            'impressions': 'sum', # Total impressions
            'ctr': 'mean',       # Average CTR
            'position': 'mean'   # Average position
        }
        
        # Group by date and rank bucket, then aggregate all metrics
        daily_metrics = df_current.groupby(['Date', 'rank_bucket']).agg(agg_functions).reset_index()
        
        # Rename columns for clarity
        daily_metrics = daily_metrics.rename(columns={
            'query': 'keywords_count',
            'clicks': 'total_clicks',
            'impressions': 'total_impressions',
            'ctr': 'avg_ctr',
            'position': 'avg_position'
        })
        
        # Create separate pivots for each metric
        metrics_data = {}
        
        # 1. Keywords Count (for stacked area chart)
        keywords_pivot = daily_metrics.pivot(
            index='Date', 
            columns='rank_bucket', 
            values='keywords_count'
        ).fillna(0)
        
        # 2. Clicks (for stacked area chart)
        clicks_pivot = daily_metrics.pivot(
            index='Date',
            columns='rank_bucket', 
            values='total_clicks'
        ).fillna(0)
        
        # 3. Impressions (for stacked area chart) 
        impressions_pivot = daily_metrics.pivot(
            index='Date',
            columns='rank_bucket',
            values='total_impressions'
        ).fillna(0)
        
        # 4. Average CTR (for line chart)
        ctr_pivot = daily_metrics.pivot(
            index='Date',
            columns='rank_bucket',
            values='avg_ctr'
        ).fillna(0)
        
        # 5. Average Position (for line chart - lower is better)
        position_pivot = daily_metrics.pivot(
            index='Date',
            columns='rank_bucket', 
            values='avg_position'
        ).fillna(0)
        
        # Ensure all dates in range are present for each metric
        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        
        pivots = {
            'keywords': keywords_pivot,
            'clicks': clicks_pivot, 
            'impressions': impressions_pivot,
            'ctr': ctr_pivot,
            'position': position_pivot
        }
        
        # Process each pivot table
        for metric_name, pivot_table in pivots.items():
            pivot_table = pivot_table.reindex(all_dates, fill_value=0)
            pivot_table = pivot_table.reindex(columns=all_buckets, fill_value=0)
            pivot_table.index.name = 'date'
            metrics_data[metric_name] = pivot_table
        
        # Combine all metrics into a comprehensive daily time series
        daily_time_series_comprehensive = []
        
        for date in all_dates:
            date_str = date.strftime('%Y-%m-%d')
            daily_record = {
                'date': date_str,
                # Keywords count by bucket
                'keywords_top_3': int(metrics_data['keywords'].loc[date, 'Top 3']),
                'keywords_top_4_10': int(metrics_data['keywords'].loc[date, 'Top 4–10']),
                'keywords_top_11_20': int(metrics_data['keywords'].loc[date, 'Top 11–20']),
                'keywords_pos_21_plus': int(metrics_data['keywords'].loc[date, 'Pos 21+']),
                
                # Clicks by bucket
                'clicks_top_3': int(metrics_data['clicks'].loc[date, 'Top 3']),
                'clicks_top_4_10': int(metrics_data['clicks'].loc[date, 'Top 4–10']),
                'clicks_top_11_20': int(metrics_data['clicks'].loc[date, 'Top 11–20']),
                'clicks_pos_21_plus': int(metrics_data['clicks'].loc[date, 'Pos 21+']),
                
                # Impressions by bucket
                'impressions_top_3': int(metrics_data['impressions'].loc[date, 'Top 3']),
                'impressions_top_4_10': int(metrics_data['impressions'].loc[date, 'Top 4–10']),
                'impressions_top_11_20': int(metrics_data['impressions'].loc[date, 'Top 11–20']),
                'impressions_pos_21_plus': int(metrics_data['impressions'].loc[date, 'Pos 21+']),
                
                # Average CTR by bucket (rounded to 4 decimal places)
                'ctr_top_3': round(float(metrics_data['ctr'].loc[date, 'Top 3']), 4),
                'ctr_top_4_10': round(float(metrics_data['ctr'].loc[date, 'Top 4–10']), 4),
                'ctr_top_11_20': round(float(metrics_data['ctr'].loc[date, 'Top 11–20']), 4),
                'ctr_pos_21_plus': round(float(metrics_data['ctr'].loc[date, 'Pos 21+']), 4),
                
                # Average Position by bucket (rounded to 1 decimal place)
                'position_top_3': round(float(metrics_data['position'].loc[date, 'Top 3']), 1),
                'position_top_4_10': round(float(metrics_data['position'].loc[date, 'Top 4–10']), 1),
                'position_top_11_20': round(float(metrics_data['position'].loc[date, 'Top 11–20']), 1),
                'position_pos_21_plus': round(float(metrics_data['position'].loc[date, 'Pos 21+']), 1),
            }
            daily_time_series_comprehensive.append(daily_record)

        # 3. IMPROVED vs DECLINED KEYWORDS
        # Calculate average position for each keyword in both periods
        cur_avg = df_current.groupby('query')['position'].mean()
        prev_avg = df_prev.groupby('query')['position'].mean()

        # Combine the averages
        pos_comparison = pd.concat([cur_avg, prev_avg], axis=1, keys=['current_avg', 'previous_avg'])
        
        # Only include keywords that appear in both periods
        pos_comparison = pos_comparison.dropna()
        
        if not pos_comparison.empty:
            # Calculate position change (negative = improvement, positive = decline)
            pos_comparison['position_change'] = pos_comparison['current_avg'] - pos_comparison['previous_avg']
            
            # IMPROVED KEYWORDS (position decreased = better ranking)
            improved = pos_comparison[pos_comparison['position_change'] < 0].copy()
            improved['improvement'] = -improved['position_change']  # Make positive for display
            improved = improved.sort_values('improvement', ascending=False).head(20)
            
            improved_keywords = improved.reset_index().rename(columns={
                'query': 'keyword',
                'current_avg': 'pos_last_30_days',
                'previous_avg': 'pos_before_30_days',
                'improvement': 'change_in_position'
            })[['keyword', 'pos_last_30_days', 'pos_before_30_days', 'change_in_position']].round(1)
            
            # DECLINED KEYWORDS (position increased = worse ranking)  
            declined = pos_comparison[pos_comparison['position_change'] > 0].copy()
            declined['decline'] = declined['position_change']
            declined = declined.sort_values('decline', ascending=False).head(20)
            
            declined_keywords = declined.reset_index().rename(columns={
                'query': 'keyword',
                'current_avg': 'pos_last_30_days', 
                'previous_avg': 'pos_before_30_days',
                'decline': 'change_in_position'
            })[['keyword', 'pos_last_30_days', 'pos_before_30_days', 'change_in_position']].round(1)
        else:
            # No overlapping keywords between periods
            improved_keywords = pd.DataFrame(columns=['keyword', 'pos_last_30_days', 'pos_before_30_days', 'change_in_position'])
            declined_keywords = pd.DataFrame(columns=['keyword', 'pos_last_30_days', 'pos_before_30_days', 'change_in_position'])

        # Prepare response
        response_data = {
            "bucket_matrix": bucket_matrix.to_dict('records'),
            "daily_time_series": daily_time_series_comprehensive,
            "improved_keywords": improved_keywords.to_dict('records'),
            "declined_keywords": declined_keywords.to_dict('records'),
            # Additional metadata for frontend filtering
            "available_metrics": ["keywords", "clicks", "impressions", "ctr", "position"],
            "date_range": {
                "start_date": start_dt.strftime('%Y-%m-%d'),
                "end_date": end_dt.strftime('%Y-%m-%d')
            }
        }

        print("Bucket Matrix:")
        print(bucket_matrix)
        print(f"\nDaily Time Series Records: {len(daily_time_series_comprehensive)}")
        print("Sample daily record:")
        if daily_time_series_comprehensive:
            print(daily_time_series_comprehensive[0])
        print("Improved Keywords Count:", len(improved_keywords))
        print("Declined Keywords Count:", len(declined_keywords))

        return response_data
    
    except Exception as e:
        print(f"Error in ranking_keywords route: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/ranking_keywords/")
async def get_ranking_keywords_analysis(data: SiteData):
    """
    Analyze ranking keywords data with comprehensive metrics.
    
    Returns:
        - Bucket matrix with ranking distribution
        - Daily time series with all metrics  
        - Improved/declined keywords
        - Summary statistics
    """
    try:
        # Initialize the analyzer
        analyzer = RankingKeywordsAnalyzer()

        search_console = SearchConsoleService(
            access_token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
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

