import pandas as pd
import json
from typing import Dict, List, Tuple, Union
import numpy as np
from abc import ABC, abstractmethod

class BaseKPICalculator(ABC):
    """Base class for all KPI calculators."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.kpis = {}
    
    @abstractmethod
    def calculate_kpis(self) -> Dict:
        """Calculate KPIs specific to this category."""
        pass

class PageTitleCalculator(BaseKPICalculator):
    """Calculate page title-related KPIs and generate detailed analysis."""
    
    def calculate_kpis(self) -> Dict:
        """Calculate all page title KPIs with specific filtering logic."""
        # Base filter: Content Type = 'text/html; charset=UTF-8'
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        html_pages = self.df[html_mask]
        total_html_pages = len(html_pages)
        
        # 1. All Page Titles: Count of all HTML pages with Title 1
        all_titles_count = total_html_pages
        
        # 2. Missing Titles: Title 1 is null, empty, or whitespace
        missing_title_mask = html_mask & (
            self.df['Title_1'].isna() | 
            (self.df['Title_1'] == '') |
            (self.df['Title_1'].astype(str).str.strip() == '')
        )
        missing_title_count = int(missing_title_mask.sum())
        missing_title_percentage = (missing_title_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 3. Duplicate Titles: Same Title 1 appears multiple times
        non_empty_titles = html_pages[html_pages['Title_1'].notna() & 
                                     (html_pages['Title_1'] != '') & 
                                     (html_pages['Title_1'].astype(str).str.strip() != '')]
        
        duplicate_titles = non_empty_titles[non_empty_titles.duplicated(subset=['Title_1'], keep=False)]
        duplicate_title_count = len(duplicate_titles)
        duplicate_title_percentage = (duplicate_title_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 4. Over 60 Characters: Title 1 Length > 60
        over_60_char_mask = html_mask & (
            self.df['Title_1_Length'].notna() & 
            (pd.to_numeric(self.df['Title_1_Length'], errors='coerce') > 60)
        )
        over_60_char_count = int(over_60_char_mask.sum())
        over_60_char_percentage = (over_60_char_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 5. Below 30 Characters: Title 1 Length < 30
        below_30_char_mask = html_mask & (
            self.df['Title_1_Length'].notna() & 
            (pd.to_numeric(self.df['Title_1_Length'], errors='coerce') < 30)
        )
        below_30_char_count = int(below_30_char_mask.sum())
        below_30_char_percentage = (below_30_char_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 6. Same as H1: Title 1 matches H1-1
        same_as_h1_mask = html_mask & (
            self.df['Title_1'].notna() & 
            self.df['H1-1'].notna() &
            (self.df['Title_1'] != '') &
            (self.df['H1-1'] != '') &
            (self.df['Title_1'].astype(str).str.strip() == self.df['H1-1'].astype(str).str.strip())
        )
        same_as_h1_count = int(same_as_h1_mask.sum())
        same_as_h1_percentage = (same_as_h1_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 7. Multiple Titles: Count pages with multiple title tags (if applicable)
        # This would need additional data from crawl, for now we'll set to 0
        multiple_titles_count = 0
        multiple_titles_percentage = 0
        
        self.kpis = {
            'page_title_kpis': {
                'all_titles': {
                    'count': all_titles_count,
                    'percentage': 100.0
                },
                'missing_title': {
                    'count': missing_title_count,
                    'percentage': round(missing_title_percentage, 1)
                },
                'duplicate_title': {
                    'count': duplicate_title_count,
                    'percentage': round(duplicate_title_percentage, 1)
                },
                'over_60_characters': {
                    'count': over_60_char_count,
                    'percentage': round(over_60_char_percentage, 1)
                },
                'below_30_characters': {
                    'count': below_30_char_count,
                    'percentage': round(below_30_char_percentage, 1)
                },
                'same_as_h1': {
                    'count': same_as_h1_count,
                    'percentage': round(same_as_h1_percentage, 1)
                },
                'multiple_titles': {
                    'count': multiple_titles_count,
                    'percentage': round(multiple_titles_percentage, 1)
                }
            }
        }
        
        return self.kpis
    
    def get_missing_title_table(self) -> pd.DataFrame:
        """Get table for pages with missing titles."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        missing_title_mask = html_mask & (
            self.df['Title_1'].isna() | 
            (self.df['Title_1'] == '') |
            (self.df['Title_1'].astype(str).str.strip() == '')
        )
        
        filtered_df = self.df[missing_title_mask]
        
        return filtered_df[['Address', 'Title_1', 'Title_1_Length','Title_1_Pixel_Width', 'H1-1']].copy()
    
    def get_duplicate_title_table(self) -> pd.DataFrame:
        """Get table for pages with duplicate titles."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        html_pages = self.df[html_mask]
        
        # Filter out empty/null titles first
        non_empty_titles = html_pages[
            html_pages['Title_1'].notna() & 
            (html_pages['Title_1'] != '') & 
            (html_pages['Title_1'].astype(str).str.strip() != '')
        ]
        
        # Find duplicates
        duplicate_titles = non_empty_titles[non_empty_titles.duplicated(subset=['Title_1'], keep=False)]
        
        return duplicate_titles[['Address', 'Title_1', 'Title_1_Length','Title_1_Pixel_Width', 'H1-1']].copy().sort_values('Title_1')
    
    def get_over_60_characters_table(self) -> pd.DataFrame:
        """Get table for pages with titles over 60 characters."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        over_60_char_mask = html_mask & (
            self.df['Title_1_Length'].notna() & 
            (pd.to_numeric(self.df['Title_1_Length'], errors='coerce') > 60)
        )
        
        filtered_df = self.df[over_60_char_mask]
        
        return filtered_df[['Address', 'Title_1', 'Title_1_Length','Title_1_Pixel_Width', 'H1-1']].copy()
    
    def get_below_30_characters_table(self) -> pd.DataFrame:
        """Get table for pages with titles below 30 characters."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        below_30_char_mask = html_mask & (
            self.df['Title_1_Length'].notna() & 
            (pd.to_numeric(self.df['Title_1_Length'], errors='coerce') < 30)
        )
        
        filtered_df = self.df[below_30_char_mask]
        
        return filtered_df[['Address', 'Title_1', 'Title_1_Length','Title_1_Pixel_Width', 'H1-1']].copy()
    
    def get_same_as_h1_table(self) -> pd.DataFrame:
        """Get table for pages where title matches H1."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        same_as_h1_mask = html_mask & (
            self.df['Title_1'].notna() & 
            self.df['H1-1'].notna() &
            (self.df['Title_1'] != '') &
            (self.df['H1-1'] != '') &
            (self.df['Title_1'].astype(str).str.strip() == self.df['H1-1'].astype(str).str.strip())
        )
        
        filtered_df = self.df[same_as_h1_mask]
        
        return filtered_df[['Address', 'Title_1', 'Title_1_Length','Title_1_Pixel_Width', 'H1-1']].copy()
    
    def get_multiple_titles_table(self) -> pd.DataFrame:
        """Get table for pages with multiple title tags (placeholder for future implementation)."""
        # This would require additional data from the crawl
        # For now, return empty DataFrame with expected columns
        return pd.DataFrame(columns=['Address', 'Title_1', 'Title_1_Length','Title_1_Pixel_Width', 'H1-1'])
    
    def export_page_title_report(self, filename: str = 'page_title_report.json') -> Dict:
        """Export detailed page title report."""
        if not self.kpis:
            self.calculate_kpis()
        
        report = {
            'kpis': self.kpis,
            'tables': {
                'missing_title': self.get_missing_title_table().to_dict('records'),
                'duplicate_title': self.get_duplicate_title_table().to_dict('records'),
                'over_60_characters': self.get_over_60_characters_table().to_dict('records'),
                'below_30_characters': self.get_below_30_characters_table().to_dict('records'),
                'same_as_h1': self.get_same_as_h1_table().to_dict('records'),
                'multiple_titles': self.get_multiple_titles_table().to_dict('records')
            }
        }
        
        return report


class DataProcessor:
    """Process crawl data and initialize it for KPI calculations."""
    
    def __init__(self, data: Union[str, dict, List[dict]], transform_column_names: bool = True):
        self.raw_data = data
        self.transform_column_names = transform_column_names
        self.df = self._process_data()
    
    def _process_data(self) -> pd.DataFrame:
        """Process input data into a pandas DataFrame."""
        if isinstance(self.raw_data, str):
            # JSON string
            try:
                parsed_data = json.loads(self.raw_data)
                return self._json_to_dataframe(parsed_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}")
        elif isinstance(self.raw_data, (dict, list)):
            return self._json_to_dataframe(self.raw_data)
        else:
            raise ValueError("Data must be JSON string, dictionary, or list of dictionaries")
    
    def _json_to_dataframe(self, json_data: Union[dict, List[dict]]) -> pd.DataFrame:
        """Convert JSON crawl data to DataFrame."""
        all_data = []
        
        # Handle different data structures
        if isinstance(json_data, list):
            # List of tabs
            for tab_data in json_data:
                if isinstance(tab_data, dict) and 'values' in tab_data:
                    df_temp = self._process_tab_data(tab_data)
                    if not df_temp.empty:
                        all_data.append(df_temp)
        elif isinstance(json_data, dict):
            # Single tab
            if 'values' in json_data:
                df_temp = self._process_tab_data(json_data)
                if not df_temp.empty:
                    all_data.append(df_temp)
        
        if not all_data:
            print("Warning: No valid data found to process")
            return pd.DataFrame()
        
        # return pd.concat(all_data, ignore_index=True)
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Transform column names if requested
        if self.transform_column_names:
            final_df.columns = [col.replace(" ", "_") for col in final_df.columns]
        
        return final_df
    
    def _process_tab_data(self, tab_data: dict) -> pd.DataFrame:
        """Process individual tab data."""
        if 'values' in tab_data and len(tab_data['values']) > 0:
            headers = tab_data['values'][0]
            data_rows = tab_data['values'][1:] if len(tab_data['values']) > 1 else []
            
            if data_rows:
                return pd.DataFrame(data_rows, columns=headers)
        
        return pd.DataFrame()
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get the processed DataFrame."""
        return self.df
    
    def get_data_info(self) -> Dict:
        """Get information about the processed data."""
        return {
            'total_rows': int(len(self.df)),
            'columns': list(self.df.columns),
            'memory_usage': int(self.df.memory_usage(deep=True).sum()),
            'tabs_processed': 1 if isinstance(self.raw_data, dict) else len(self.raw_data) if isinstance(self.raw_data, list) else 0
        }


def page_title_kpis_and_table(data):
    """Main function to process data and generate page title KPIs and tables."""
    
    try:
        # Wrap single data object in list if needed
        if isinstance(data, dict):
            data_process = [data]
        else:
            data_process = data
        
        # Process the data
        processor = DataProcessor(data_process)
        df = processor.get_dataframe()
        
        if df.empty:
            print("Error: No data to process")
            return None
        
        print("Data Info:")
        print(json.dumps(processor.get_data_info(), indent=2))
        print("\n" + "="*50 + "\n")
        
        # Calculate Page Title KPIs
        page_title_calc = PageTitleCalculator(df)
        page_title_kpis = page_title_calc.calculate_kpis()
        
        print(page_title_kpis)
        
        # Export full report
        full_result = page_title_calc.export_page_title_report('page_title_analysis.json')
        
        return full_result
        
    except Exception as e:
        print(f"Error processing data: {e}")
        return None


# Example usage
# if __name__ == "__main__":
#     # Test with sample data
#     sample_data = {
#         'values': [
#             ['Address', 'Content Type', 'Title 1', 'Title 1 Length', 'H1-1'],
#             ['https://example.com', 'text/html; charset=UTF-8', 'Home Page', '9', 'Home Page'],
#             ['https://example.com/page1', 'text/html; charset=UTF-8', '', '0', 'Page 1'],
#             ['https://example.com/page2', 'text/html; charset=UTF-8', 'This is a very long title that exceeds sixty characters limit', '65', 'Page 2'],
#             ['https://example.com/page3', 'text/html; charset=UTF-8', 'Short', '5', 'Different H1'],
#             ['https://example.com/page4', 'text/html; charset=UTF-8', 'Home Page', '9', 'Home Page'],
#         ]
#     }
    
#     result = page_title_kpis_and_table(sample_data)
#     if result:
#         print("Page Title KPIs calculated successfully!")
#         print(json.dumps(result['kpis'], indent=2))