from googleapiclient.discovery import build
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")





class SearchConsoleService:
    """Service class for Google Search Console operations"""
    
    def __init__(self, access_token: str, refresh_token: str, client_id: str, client_secret: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.service = None
    
    def connect(self):
        """Establish connection to Google Search Console API"""
        try:
            creds = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            )
            self.service = build('webmasters', 'v3', credentials=creds)
            return self.service
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
    def get_site_data(self, site_url: str, device: str, country: str, search_type: str, 
                      start_date: str, end_date: str) -> list:
        """Fetch site data from Google Search Console"""
        if not self.service:
            self.connect()
        
        # Build payload
        payload = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['query', 'page', 'country', 'date', 'device'],  # Fixed capitalization
            'type': search_type,
            'dimensionFilterGroups': [{
                'filters': [{
                    "dimension": "country",
                    'expression': country
                }]
            }],
            'rowLimit': 25000
        }

        # Add device filter if not "all" - when "all", we want data from all devices
        if device.lower() != "all":
            payload['dimensionFilterGroups'][0]['filters'].append({
                'dimension': 'device',
                'expression': device
            })
        
        try:
            all_rows = []
            start_row = 0
            
            while True:
                # Add pagination
                current_payload = payload.copy()
                current_payload['startRow'] = start_row
                
                response = self.service.searchanalytics().query(
                    siteUrl=site_url, 
                    body=current_payload
                ).execute()
                
                rows = response.get('rows', [])
                if not rows:
                    break
                
                all_rows.extend(rows)
                
                # Check if we got fewer rows than requested (end of data)
                if len(rows) < 25000:
                    break
                
                start_row += len(rows)
            
            return all_rows
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching site data: {str(e)}")

class DataProcessor:
    """Class for processing Search Console data"""
    
    @staticmethod
    def structure_dataframe(data: list) -> pd.DataFrame:
        """Convert API response to structured DataFrame"""
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Extract keys into separate columns
        keys_df = pd.DataFrame(
            df['keys'].tolist(),
            columns=['query', 'page', 'country', 'date', 'device']  # Fixed capitalization
        )
        
        # Combine with metrics
        df = pd.concat([keys_df, df.drop(columns=['keys'])], axis=1)
        
        # Convert data types
        df['date'] = pd.to_datetime(df['date'])  # Fixed column name
        numeric_columns = ['clicks', 'impressions', 'ctr', 'position']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')
        
        return df
    
    @staticmethod
    def summarize_metrics(df: pd.DataFrame) -> dict:
        """Summarize key metrics from dataframe including Ranking Keywords and Ranking URLs"""
        if df.empty:
            return {
                'Clicks': 0,
                'Impressions': 0,
                'CTR': 0,
                'AvgPosition': 0,
                'Ranking_Keywords': 0,
                'Ranking_URLs': 0
            }
        
        total_clicks = df['clicks'].sum()
        total_impressions = df['impressions'].sum()
        ctr = (total_clicks / total_impressions) * 100 if total_impressions > 0 else 0
        avg_position = df['position'].mean()
        unique_keywords = df['query'].nunique()
        unique_urls = df['page'].nunique()
        
        return {
            'Clicks': int(total_clicks),
            'Impressions': int(total_impressions),
            'CTR': round(float(ctr), 2),
            'AvgPosition': round(float(avg_position), 2),
            'Ranking_Keywords': int(unique_keywords),
            'Ranking_URLs': int(unique_urls)
        }
        
    @staticmethod
    def compare_metrics(current: dict, previous: dict) -> dict:
        """Compare current vs previous metrics with proper percentage calculations"""
        result = {}
        
        for key in current:
            curr_val = current[key]
            prev_val = previous.get(key, 0)
            
            if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)):
                diff = curr_val - prev_val
                
                # Calculate percentage change based on metric type
                if key in ['Clicks', 'Impressions']:
                    # For counts: standard percentage change
                    pct_change = ((diff / prev_val) * 100) if prev_val != 0 else (100 if curr_val > 0 else 0)
                    
                elif key == 'CTR':
                    # For CTR: percentage point change and relative change
                    percentage_point_change = diff  # This is already in percentage points
                    relative_change = ((diff / prev_val) * 100) if prev_val != 0 else (100 if curr_val > 0 else 0)
                    
                    result[key] = {
                        'Current': round(curr_val, 2),
                        'Previous': round(prev_val, 2),
                        'Difference': round(diff, 2),
                        'Percentage_Point_Change': round(percentage_point_change, 2),
                        'Relative_Change (%)': round(relative_change, 1),
                        'Change_Type': 'CTR_Special'
                    }
                    continue
                    
                elif key == 'AvgPosition':
                    # For position: lower is better, so we need to interpret changes differently
                    position_improvement = -diff  # Negative diff means position improved (lower number)
                    pct_change = ((diff / prev_val) * 100) if prev_val != 0 else 0
                    
                    # Position interpretation
                    if diff < 0:
                        change_direction = "Improved"
                    elif diff > 0:
                        change_direction = "Declined"
                    else:
                        change_direction = "No Change"
                    
                    result[key] = {
                        'Current': round(curr_val, 2),
                        'Previous': round(prev_val, 2),
                        'Difference': round(diff, 2),
                        'Position_Change': round(position_improvement, 2),
                        'Relative_Change (%)': round(abs(pct_change), 1),
                        'Direction': change_direction,
                        'Change_Type': 'Position_Special'
                    }
                    continue
                    
                else:
                    # Default calculation for other metrics
                    pct_change = ((diff / prev_val) * 100) if prev_val != 0 else (100 if curr_val > 0 else 0)
                
                # Standard result format for Clicks and Impressions
                result[key] = {
                    'Current': curr_val if key in ['Clicks', 'Impressions'] else round(curr_val, 2),
                    'Previous': prev_val if key in ['Clicks', 'Impressions'] else round(prev_val, 2),
                    'Difference': round(diff, 2),
                    'Change (%)': round(pct_change, 1),
                    'Change_Direction': 'Increase' if diff > 0 else ('Decrease' if diff < 0 else 'No Change')
                }
            else:
                result[key] = "Non-numeric comparison not supported"
        
        return result
    
    @staticmethod
    def create_comparison_matrix(df: pd.DataFrame) -> dict:
        """Create comparison matrix by splitting data into two periods"""
        if df.empty:
            return {}
        
        df = df.sort_values('date')  # Fixed column name
        start_date = df['date'].min()
        end_date = df['date'].max()
        
        # Calculate midpoint
        mid_date = start_date + (end_date - start_date) / 2
        mid_date = pd.to_datetime(mid_date).floor('D')
        
        # Split into two halves
        previous_df = df[(df['date'] >= start_date) & (df['date'] < mid_date)]
        current_df = df[(df['date'] >= mid_date) & (df['date'] <= end_date)]
        
        current_metrics = DataProcessor.summarize_metrics(current_df)
        previous_metrics = DataProcessor.summarize_metrics(previous_df)
        
        return DataProcessor.compare_metrics(current_metrics, previous_metrics)
    
    @staticmethod
    def create_device_performance_comparison(df: pd.DataFrame, original_start_date: str, original_end_date: str) -> dict:
        """Create device-based performance comparison between current and previous periods"""
        if df.empty:
            return {}
        
        df = df.sort_values('date')
        
        # Parse original date range
        original_start = pd.to_datetime(original_start_date)
        original_end = pd.to_datetime(original_end_date)
        
        # Split data into current (original range) and previous periods
        current_period = df[(df['date'] >= original_start) & (df['date'] <= original_end)]
        previous_period = df[df['date'] < original_start]
        
        device_comparison = {}
        device_summary = {
            'total_devices': 0,
            'best_performing_device': None,
            'highest_growth_device': None,
            'performance_overview': {}
        }
        
        # Get all unique devices
        all_devices = df['device'].unique()
        device_summary['total_devices'] = len(all_devices)
        
        best_clicks = 0
        highest_growth = -float('inf')
        
        for device in all_devices:
            # Filter data for current device
            current_device_data = current_period[current_period['device'] == device]
            previous_device_data = previous_period[previous_period['device'] == device]
            
            # Calculate metrics for each period
            current_metrics = DataProcessor.summarize_metrics(current_device_data)
            previous_metrics = DataProcessor.summarize_metrics(previous_device_data)
            
            # Compare metrics
            device_comparison[device] = DataProcessor.compare_metrics(current_metrics, previous_metrics)
            
            # Track best performing device (by current clicks)
            if current_metrics['Clicks'] > best_clicks:
                best_clicks = current_metrics['Clicks']
                device_summary['best_performing_device'] = device
            
            # Track highest growth device (by click percentage change)
            if 'Clicks' in device_comparison[device] and 'Change (%)' in device_comparison[device]['Clicks']:
                click_growth = device_comparison[device]['Clicks']['Change (%)']
                if click_growth > highest_growth:
                    highest_growth = click_growth
                    device_summary['highest_growth_device'] = device
            
            # Add additional device-specific stats
            device_comparison[device]['current_period_stats'] = {
                'total_queries': len(current_device_data),
                'unique_pages': current_device_data['page'].nunique() if not current_device_data.empty else 0,
                'date_range': f"{original_start_date} to {original_end_date}",
                'avg_daily_clicks': round(current_metrics['Clicks'] / max(1, (original_end - original_start).days), 2)
            }
            device_comparison[device]['previous_period_stats'] = {
                'total_queries': len(previous_device_data),
                'unique_pages': previous_device_data['page'].nunique() if not previous_device_data.empty else 0,
                'date_range': f"{previous_period['date'].min().strftime('%Y-%m-%d') if not previous_period.empty else 'N/A'} to {(original_start - pd.Timedelta(days=1)).strftime('%Y-%m-%d')}",
                'avg_daily_clicks': round(previous_metrics['Clicks'] / max(1, len(previous_device_data) // 30 if len(previous_device_data) > 0 else 1), 2)
            }
            
            # Add performance overview for this device
            device_summary['performance_overview'][device] = {
                'current_clicks': current_metrics['Clicks'],
                'click_change_pct': device_comparison[device]['Clicks']['Change (%)'] if 'Clicks' in device_comparison[device] else 0,
                'current_ctr': current_metrics['CTR'],
                'position_change': device_comparison[device]['AvgPosition']['Direction'] if 'AvgPosition' in device_comparison[device] else 'No Change'
            }
        
        return {
            'device_comparisons': device_comparison,
            'summary': device_summary
        }
    
    @staticmethod
    def create_device_distribution_data(df: pd.DataFrame, original_start_date: str, original_end_date: str) -> dict:
        """Create device distribution data for pie chart visualization"""
        if df.empty:
            return {}
        
        # Filter to current period only
        original_start = pd.to_datetime(original_start_date)
        original_end = pd.to_datetime(original_end_date)
        current_period = df[(df['date'] >= original_start) & (df['date'] <= original_end)]
        
        if current_period.empty:
            return {}
        
        # Group by device and sum clicks
        device_clicks = current_period.groupby('device')['clicks'].sum().sort_values(ascending=False)
        total_clicks = device_clicks.sum()
        
        # Create pie chart data
        pie_data = []
        device_stats = []
        
        for device, clicks in device_clicks.items():
            percentage = (clicks / total_clicks * 100) if total_clicks > 0 else 0
            
            pie_data.append({
                'device': device,
                'Clicks': int(clicks),
                'percentage': round(percentage, 1)
            })
            
            # Get additional stats for this device
            device_data = current_period[current_period['device'] == device]
            device_stats.append({
                'device': device,
                'clicks': int(clicks),
                'impressions': int(device_data['impressions'].sum()),
                'ctr': round(device_data['ctr'].mean(), 2),
                'avg_position': round(device_data['position'].mean(), 2),
                'percentage': round(percentage, 1)
            })
        
        return {
            'pie_chart_data': pie_data,
            'device_stats': device_stats,
            'total_clicks': int(total_clicks)
        }
    
    @staticmethod
    def classify_rank(position: float) -> str:
        """Classify position into rank groups"""
        if position <= 3:
            return 'Top 3'
        elif position <= 10:
            return 'Top 10'
        else:
            return 'Top 20+'
    
    @staticmethod
    def prepare_line_plot_data(df: pd.DataFrame) -> tuple:
        """Prepare data for line plot visualization"""
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        df['date'] = pd.to_datetime(df['date'])  # Fixed column name
        
        # Group by date and aggregate metrics
        daily = df.groupby('date').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).asfreq('D', fill_value=0)
        
        # Split into two periods
        half_days = len(daily) // 2
        period1 = daily.iloc[:half_days]
        period2 = daily.iloc[half_days:]
        
        return period1, period2

def convert_numpy_types(data):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(data, dict):
        return {key: convert_numpy_types(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_types(item) for item in data]
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data