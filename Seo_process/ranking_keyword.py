import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np

class RankingKeywordsAnalyzer:
    """
    A comprehensive class to analyze SEO ranking keywords data.
    Handles data processing, period comparisons, and metric calculations.
    """
    
    def __init__(self):
        self.all_buckets = ["Top 3", "Top 4–10", "Top 11–20", "Pos 21+"]
        self.df_current = None
        self.df_prev = None
        self.df_combined = None
        
    def analyze_keywords(self, 
                        site_url: str,
                        device_type: str,
                        country: str,
                        search_type: str,
                        start_date: str,
                        end_date: str,
                        get_site_data_func) -> Dict[str, Any]:
        """
        Main method to analyze ranking keywords data.
        
        Args:
            site_url: Website URL to analyze
            device_type: Device type (DESKTOP, MOBILE, TABLET)
            country: Country code (e.g., 'usa')
            search_type: Search type (WEB, IMAGE, VIDEO)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            get_site_data_func: Function to fetch raw data
            
        Returns:
            Dict containing all analyzed data
        """
        try:
            # 1. Parse dates and calculate periods
            start_dt, end_dt, prev_start_dt, prev_end_dt = self._calculate_periods(start_date, end_date)
            print(f"Analyzing keywords from {start_dt} to {end_dt} (previous: {prev_start_dt} to {prev_end_dt})")
            
            # 2. Fetch and structure data
            raw_data = get_site_data_func(
                site_url=site_url,
                device=device_type,
                country=country,
                search_type=search_type,
                start_date=prev_start_dt.strftime("%Y-%m-%d"),
                end_date=end_dt.strftime("%Y-%m-%d")
            )
            
            if not raw_data:
                return self._empty_response()
            
            # 3. Structure dataframe and split periods
            self.df_combined = self._structure_dataframe(raw_data)
            if self.df_combined.empty:
                return self._empty_response()
                
            self._split_periods(start_dt, end_dt, prev_start_dt, prev_end_dt)
            
            # 4. Generate all analysis components
            bucket_matrix = self._calculate_bucket_matrix()
            daily_time_series = self._calculate_daily_time_series(start_dt, end_dt)
            improved_keywords, declined_keywords = self._calculate_keyword_changes()
            
            # 5. Return comprehensive response
            return {
                "bucket_matrix": bucket_matrix,
                "daily_time_series": daily_time_series,
                "improved_keywords": improved_keywords,
                "declined_keywords": declined_keywords,
                "available_metrics": ["keywords", "clicks", "impressions", "ctr", "position"],
                "date_range": {
                    "start_date": start_dt.strftime('%Y-%m-%d'),
                    "end_date": end_dt.strftime('%Y-%m-%d')
                },
                # "summary_stats": self._calculate_summary_stats()
            }
            
        except Exception as e:
            raise Exception(f"Error in RankingKeywordsAnalyzer: {str(e)}")
    
    def _calculate_periods(self, start_date: str, end_date: str) -> tuple:
        """Calculate current and previous periods."""
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        n_days = (end_dt - start_dt).days + 1
        
        prev_end_dt = start_dt - timedelta(days=1)
        prev_start_dt = prev_end_dt - timedelta(days=n_days - 1)
        
        return start_dt, end_dt, prev_start_dt, prev_end_dt
    
    def _structure_dataframe(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Convert raw data to structured DataFrame."""
        try:
            if not raw_data or len(raw_data) == 0:
                return pd.DataFrame()
            
            df = pd.DataFrame(raw_data)
            keys_df = pd.DataFrame(df['keys'].tolist(),columns=['query','page','country','Date','device'])
            df = pd.concat([keys_df, df.drop(columns=['keys'])], axis=1)
            df['Date'] = pd.to_datetime(df['Date'])
            df[['clicks','impressions','ctr','position']] = df[['clicks','impressions','ctr','position']].apply(pd.to_numeric)

            # Ensure Date column is datetime
            # df['Date'] = pd.to_datetime(df['Date'])
            
            # Add ranking bucket
            df['rank_bucket'] = df['position'].apply(self._classify_bucket)
            
            return df
            
        except Exception as e:
            print(f"Error structuring dataframe: {str(e)}")
            return pd.DataFrame()
    
    def _classify_bucket(self, pos: float) -> str:
        """Classify position into ranking bucket."""
        if pd.isna(pos) or pos > 100:
            return "Pos 21+"
        if pos <= 3:
            return "Top 3"
        elif pos <= 10:
            return "Top 4–10"
        elif pos <= 20:
            return "Top 11–20"
        else:
            return "Pos 21+"
    
    def _split_periods(self, start_dt, end_dt, prev_start_dt, prev_end_dt):
        """Split combined dataframe into current and previous periods."""
        mask_cur = (self.df_combined['Date'] >= start_dt) & (self.df_combined['Date'] <= end_dt)
        mask_prv = (self.df_combined['Date'] >= prev_start_dt) & (self.df_combined['Date'] <= prev_end_dt)
        
        self.df_current = self.df_combined.loc[mask_cur].copy()
        self.df_prev = self.df_combined.loc[mask_prv].copy()
    
    def _calculate_bucket_matrix(self) -> List[Dict]:
        """Calculate bucket matrix with counts and changes."""
        # Count unique keywords per bucket
        cur_counts = (
            self.df_current.groupby('rank_bucket')['query']
            .nunique()
            .reindex(self.all_buckets, fill_value=0)
        )
        
        prev_counts = (
            self.df_prev.groupby('rank_bucket')['query']
            .nunique()
            .reindex(self.all_buckets, fill_value=0)
        )
        
        bucket_matrix = pd.DataFrame({
            'rank_bucket': self.all_buckets,
            'current_count': cur_counts.values,
            'previous_count': prev_counts.values
        })
        
        bucket_matrix['delta_abs'] = bucket_matrix['current_count'] - bucket_matrix['previous_count']
        
        # Calculate percentage change
        bucket_matrix['delta_pct'] = bucket_matrix.apply(
            lambda row: (
                (row['current_count'] - row['previous_count']) / row['previous_count'] * 100
                if row['previous_count'] > 0 
                else (100 if row['current_count'] > 0 else 0)
            ), axis=1
        ).round(1)
        
        return bucket_matrix.to_dict('records')
    
    def _calculate_daily_time_series(self, start_dt, end_dt) -> List[Dict]:
        """Calculate comprehensive daily time series with all metrics."""
        # Prepare aggregation functions
        agg_functions = {
            'query': 'nunique',
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }
        
        # Group by date and rank bucket
        daily_metrics = self.df_current.groupby(['Date', 'rank_bucket']).agg(agg_functions).reset_index()
        daily_metrics = daily_metrics.rename(columns={
            'query': 'keywords_count',
            'clicks': 'total_clicks',
            'impressions': 'total_impressions',
            'ctr': 'avg_ctr',
            'position': 'avg_position'
        })
        
        # Create pivot tables for each metric
        metrics_pivots = {}
        for metric in ['keywords_count', 'total_clicks', 'total_impressions', 'avg_ctr', 'avg_position']:
            pivot = daily_metrics.pivot(
                index='Date',
                columns='rank_bucket',
                values=metric
            ).fillna(0)
            
            # Ensure all dates and buckets are present
            all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
            pivot = pivot.reindex(all_dates, fill_value=0)
            pivot = pivot.reindex(columns=self.all_buckets, fill_value=0)
            
            metrics_pivots[metric] = pivot
        
        # Combine into comprehensive daily records
        daily_time_series = []
        for date in pd.date_range(start=start_dt, end=end_dt, freq='D'):
            daily_record = {
                'date': date.strftime('%Y-%m-%d'),
                # Keywords count
                'keywords_top_3': int(metrics_pivots['keywords_count'].loc[date, 'Top 3']),
                'keywords_top_4_10': int(metrics_pivots['keywords_count'].loc[date, 'Top 4–10']),
                'keywords_top_11_20': int(metrics_pivots['keywords_count'].loc[date, 'Top 11–20']),
                'keywords_pos_21_plus': int(metrics_pivots['keywords_count'].loc[date, 'Pos 21+']),
                
                # Clicks
                'clicks_top_3': int(metrics_pivots['total_clicks'].loc[date, 'Top 3']),
                'clicks_top_4_10': int(metrics_pivots['total_clicks'].loc[date, 'Top 4–10']),
                'clicks_top_11_20': int(metrics_pivots['total_clicks'].loc[date, 'Top 11–20']),
                'clicks_pos_21_plus': int(metrics_pivots['total_clicks'].loc[date, 'Pos 21+']),
                
                # Impressions
                'impressions_top_3': int(metrics_pivots['total_impressions'].loc[date, 'Top 3']),
                'impressions_top_4_10': int(metrics_pivots['total_impressions'].loc[date, 'Top 4–10']),
                'impressions_top_11_20': int(metrics_pivots['total_impressions'].loc[date, 'Top 11–20']),
                'impressions_pos_21_plus': int(metrics_pivots['total_impressions'].loc[date, 'Pos 21+']),
                
                # CTR (keep as decimal, frontend will convert to percentage)
                'ctr_top_3': round(float(metrics_pivots['avg_ctr'].loc[date, 'Top 3']), 4),
                'ctr_top_4_10': round(float(metrics_pivots['avg_ctr'].loc[date, 'Top 4–10']), 4),
                'ctr_top_11_20': round(float(metrics_pivots['avg_ctr'].loc[date, 'Top 11–20']), 4),
                'ctr_pos_21_plus': round(float(metrics_pivots['avg_ctr'].loc[date, 'Pos 21+']), 4),
                
                # Average Position
                'position_top_3': round(float(metrics_pivots['avg_position'].loc[date, 'Top 3']), 1),
                'position_top_4_10': round(float(metrics_pivots['avg_position'].loc[date, 'Top 4–10']), 1),
                'position_top_11_20': round(float(metrics_pivots['avg_position'].loc[date, 'Top 11–20']), 1),
                'position_pos_21_plus': round(float(metrics_pivots['avg_position'].loc[date, 'Pos 21+']), 1),
            }
            daily_time_series.append(daily_record)
        
        return daily_time_series
    
    def _calculate_keyword_changes(self) -> tuple:
        """Calculate improved and declined keywords with clicks, impressions, CTR and position changes."""
        
        # Calculate aggregated metrics for each keyword in both periods
        current_metrics = self.df_current.groupby('query').agg({
            'position': 'mean',
            'clicks': 'sum',
            'impressions': 'sum'
        }).round(1)
        
        prev_metrics = self.df_prev.groupby('query').agg({
            'position': 'mean',
            'clicks': 'sum',
            'impressions': 'sum'
        }).round(1)
        
        # Calculate CTR for both periods
        current_metrics['ctr'] = (current_metrics['clicks'] / current_metrics['impressions'] * 100).round(2)
        prev_metrics['ctr'] = (prev_metrics['clicks'] / prev_metrics['impressions'] * 100).round(2)
        
        # Handle division by zero for CTR
        current_metrics['ctr'] = current_metrics['ctr'].fillna(0)
        prev_metrics['ctr'] = prev_metrics['ctr'].fillna(0)
        
        # Combine metrics (only keywords present in both periods)
        metrics_comparison = pd.concat([current_metrics, prev_metrics], axis=1, 
                                    keys=['current', 'previous'], join='inner')
        
        if metrics_comparison.empty:
            empty_df = pd.DataFrame(columns=[
                'keyword', 'pos_last_30_days', 'pos_before_30_days', 'change_in_position',
                'clicks_last_30_days', 'clicks_before_30_days', 'change_in_clicks',
                'impressions_last_30_days', 'impressions_before_30_days', 'change_in_impressions',
                'ctr_last_30_days', 'ctr_before_30_days', 'change_in_ctr'
            ])
            return empty_df.to_dict('records'), empty_df.to_dict('records')
        
        # Calculate changes for all metrics
        metrics_comparison['position_change'] = (metrics_comparison[('current', 'position')] - 
                                            metrics_comparison[('previous', 'position')])
        metrics_comparison['clicks_change'] = (metrics_comparison[('current', 'clicks')] - 
                                            metrics_comparison[('previous', 'clicks')])
        metrics_comparison['impressions_change'] = (metrics_comparison[('current', 'impressions')] - 
                                                metrics_comparison[('previous', 'impressions')])
        metrics_comparison['ctr_change'] = (metrics_comparison[('current', 'ctr')] - 
                                        metrics_comparison[('previous', 'ctr')])
        
        # IMPROVED KEYWORDS (position decreased = better ranking OR clicks/impressions/CTR increased)
        # Primary criteria: position improvement (negative change)
        # Secondary criteria: clicks, impressions, or CTR improvement when position is same/worse
        improved_mask = (
            (metrics_comparison['position_change'] < 0) |  # Position improved
            ((metrics_comparison['position_change'] >= 0) & 
            ((metrics_comparison['clicks_change'] > 0) | 
            (metrics_comparison['impressions_change'] > 0) | 
            (metrics_comparison['ctr_change'] > 0)))
        )
        
        improved = metrics_comparison[improved_mask].copy()
        
        # Calculate improvement score (negative position change is good, positive others are good)
        improved['improvement_score'] = (
            -improved['position_change'] * 0.4 +  # Position weight: 40%
            improved['clicks_change'] * 0.001 +   # Clicks weight: small but meaningful
            improved['impressions_change'] * 0.0001 +  # Impressions weight: smaller
            improved['ctr_change'] * 0.1  # CTR weight: 10%
        )
        
        improved = improved.sort_values('improvement_score', ascending=False).head(50)
        
        # Format improved keywords dataframe
        improved_keywords = pd.DataFrame({
            'keyword': improved.index,
            'position_last_30_days': improved[('current', 'position')].values,
            'position_before_30_days': improved[('previous', 'position')].values,
            'change_in_position': improved['position_change'].values,
            'clicks_last_30_days': improved[('current', 'clicks')].values,
            'clicks_before_30_days': improved[('previous', 'clicks')].values,
            'change_in_clicks': improved['clicks_change'].values,
            'impressions_last_30_days': improved[('current', 'impressions')].values,
            'impressions_before_30_days': improved[('previous', 'impressions')].values,
            'change_in_impressions': improved['impressions_change'].values,
            'ctr_last_30_days': improved[('current', 'ctr')].values,
            'ctr_before_30_days': improved[('previous', 'ctr')].values,
            'change_in_ctr': improved['ctr_change'].values
        })
        
        # DECLINED KEYWORDS (position increased = worse ranking AND/OR clicks/impressions/CTR decreased)
        declined_mask = (
            (metrics_comparison['position_change'] > 0) |  # Position declined
            ((metrics_comparison['position_change'] <= 0) & 
            ((metrics_comparison['clicks_change'] < 0) | 
            (metrics_comparison['impressions_change'] < 0) | 
            (metrics_comparison['ctr_change'] < 0)))
        )
        
        declined = metrics_comparison[declined_mask].copy()
        
        # Calculate decline score (positive position change is bad, negative others are bad)
        declined['decline_score'] = (
            declined['position_change'] * 0.4 +  # Position weight: 40%
            -declined['clicks_change'] * 0.001 +  # Clicks weight: small but meaningful
            -declined['impressions_change'] * 0.0001 +  # Impressions weight: smaller
            -declined['ctr_change'] * 0.1  # CTR weight: 10%
        )
        
        declined = declined.sort_values('decline_score', ascending=False).head(50)
        
        # Format declined keywords dataframe
        declined_keywords = pd.DataFrame({
            'keyword': declined.index,
            'position_last_30_days': declined[('current', 'position')].values,
            'position_before_30_days': declined[('previous', 'position')].values,
            'change_in_position': declined['position_change'].values,
            'clicks_last_30_days': declined[('current', 'clicks')].values,
            'clicks_before_30_days': declined[('previous', 'clicks')].values,
            'change_in_clicks': declined['clicks_change'].values,
            'impressions_last_30_days': declined[('current', 'impressions')].values,
            'impressions_before_30_days': declined[('previous', 'impressions')].values,
            'change_in_impressions': declined['impressions_change'].values,
            'ctr_last_30_days': declined[('current', 'ctr')].values,
            'ctr_before_30_days': declined[('previous', 'ctr')].values,
            'change_in_ctr': declined['ctr_change'].values
        })
        
        # Round all numeric columns
        numeric_columns = [col for col in improved_keywords.columns if col != 'keyword']
        improved_keywords[numeric_columns] = improved_keywords[numeric_columns].round(2)
        declined_keywords[numeric_columns] = declined_keywords[numeric_columns].round(2)
        
        return improved_keywords.to_dict('records'), declined_keywords.to_dict('records')
    
    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics for the dashboard."""
        if self.df_current.empty or self.df_prev.empty:
            return {}
        
        current_stats = {
            'total_keywords': self.df_current['query'].nunique(),
            'total_clicks': self.df_current['clicks'].sum(),
            'total_impressions': self.df_current['impressions'].sum(),
            'avg_ctr': self.df_current['ctr'].mean(),
            'avg_position': self.df_current['position'].mean()
        }
        
        previous_stats = {
            'total_keywords': self.df_prev['query'].nunique(),
            'total_clicks': self.df_prev['clicks'].sum(),
            'total_impressions': self.df_prev['impressions'].sum(),
            'avg_ctr': self.df_prev['ctr'].mean(),
            'avg_position': self.df_prev['position'].mean()
        }
        
        # Calculate changes
        changes = {}
        for key in current_stats:
            if previous_stats[key] != 0:
                changes[f'{key}_change_pct'] = round(
                    ((current_stats[key] - previous_stats[key]) / previous_stats[key]) * 100, 1
                )
            else:
                changes[f'{key}_change_pct'] = 100 if current_stats[key] > 0 else 0
        
        return {
            'current_period': current_stats,
            'previous_period': previous_stats,
            'changes': changes
        }
    
    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response structure when no data is found."""
        return {
            "bucket_matrix": [],
            "daily_time_series": [],
            "improved_keywords": [],
            "declined_keywords": [],
            "available_metrics": ["keywords", "clicks", "impressions", "ctr", "position"],
            "date_range": {"start_date": "", "end_date": ""},
            "summary_stats": {}
        }

# Additional utility functions that can be used independently

class SEOMetricsCalculator:
    """Additional SEO metrics and calculations."""
    
    @staticmethod
    def calculate_visibility_score(df: pd.DataFrame) -> float:
        """Calculate SEO visibility score based on CTR and position."""
        if df.empty:
            return 0.0
        
        # Weight CTR by impressions and adjust by position
        weighted_score = (df['ctr'] * df['impressions'] * (100 - df['position'])).sum()
        total_possible = df['impressions'].sum() * 100
        
        return round((weighted_score / total_possible) * 100, 2) if total_possible > 0 else 0.0
    
    @staticmethod
    def detect_keyword_cannibalization(df: pd.DataFrame) -> List[Dict]:
        """Detect potential keyword cannibalization."""
        cannibalization_issues = []
        
        # Group by query and count unique URLs
        query_urls = df.groupby('query')['page'].nunique().reset_index()
        query_urls = query_urls[query_urls['page'] > 1]  # Multiple URLs for same query
        
        for _, row in query_urls.iterrows():
            query = row['query']
            query_data = df[df['query'] == query]
            urls = query_data['page'].unique()
            
            cannibalization_issues.append({
                'keyword': query,
                'competing_urls': list(urls),
                'avg_position': query_data['position'].mean(),
                'total_impressions': query_data['impressions'].sum()
            })
        
        return sorted(cannibalization_issues, key=lambda x: x['total_impressions'], reverse=True)[:10]
    



# Simplified API route using the RankingKeywordsAnalyzer class

# from fastapi import HTTPException


# @router.post("/ranking_keywords/")
# async def get_ranking_keywords_analysis(data: SiteData):
#     """
#     Analyze ranking keywords data with comprehensive metrics.
    
#     Returns:
#         - Bucket matrix with ranking distribution
#         - Daily time series with all metrics  
#         - Improved/declined keywords
#         - Summary statistics
#     """
#     try:
#         # Initialize the analyzer
#         analyzer = RankingKeywordsAnalyzer()
        
#         # Perform complete analysis
#         result = analyzer.analyze_keywords(
#             site_url=data.site_url,
#             device_type=data.device_type,
#             country=data.country,
#             search_type=data.search_type,
#             start_date=data.start_date,
#             end_date=data.end_date,
#             get_site_data_func=get_site_data  # Your existing data fetching function
#         )
        
#         # Optional: Add additional SEO metrics
#         if analyzer.df_current is not None and not analyzer.df_current.empty:
#             # Calculate visibility score
#             visibility_score = SEOMetricsCalculator.calculate_visibility_score(analyzer.df_current)
#             result['visibility_score'] = visibility_score
            
#             # Detect keyword cannibalization
#             cannibalization_issues = SEOMetricsCalculator.detect_keyword_cannibalization(analyzer.df_current)
#             result['cannibalization_issues'] = cannibalization_issues
        
#         return result
        
#     except Exception as e:
#         print(f"Error in ranking keywords analysis: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# # Alternative route for specific analysis types
# @router.post("/ranking_keywords/bucket_analysis/")
# async def get_bucket_analysis_only(data: SiteData):
#     """Get only bucket matrix analysis."""
#     try:
#         analyzer = RankingKeywordsAnalyzer()
#         result = analyzer.analyze_keywords(
#             site_url=data.site_url,
#             device_type=data.device_type,
#             country=data.country,
#             search_type=data.search_type,
#             start_date=data.start_date,
#             end_date=data.end_date,
#             get_site_data_func=get_site_data
#         )
        
#         return {
#             "bucket_matrix": result["bucket_matrix"],
#             "summary_stats": result["summary_stats"]
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Bucket analysis failed: {str(e)}")


# @router.post("/ranking_keywords/time_series/")
# async def get_time_series_only(data: SiteData):
#     """Get only time series data for charts."""
#     try:
#         analyzer = RankingKeywordsAnalyzer()
#         result = analyzer.analyze_keywords(
#             site_url=data.site_url,
#             device_type=data.device_type,
#             country=data.country,
#             search_type=data.search_type,
#             start_date=data.start_date,
#             end_date=data.end_date,
#             get_site_data_func=get_site_data
#         )
        
#         return {
#             "daily_time_series": result["daily_time_series"],
#             "available_metrics": result["available_metrics"],
#             "date_range": result["date_range"]
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Time series analysis failed: {str(e)}")


# @router.post("/ranking_keywords/keyword_changes/")
# async def get_keyword_changes_only(data: SiteData):
#     """Get only improved/declined keywords."""
#     try:
#         analyzer = RankingKeywordsAnalyzer()
#         result = analyzer.analyze_keywords(
#             site_url=data.site_url,
#             device_type=data.device_type,
#             country=data.country,
#             search_type=data.search_type,
#             start_date=data.start_date,
#             end_date=data.end_date,
#             get_site_data_func=get_site_data
#         )
        
#         return {
#             "improved_keywords": result["improved_keywords"],
#             "declined_keywords": result["declined_keywords"]
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Keyword changes analysis failed: {str(e)}")


