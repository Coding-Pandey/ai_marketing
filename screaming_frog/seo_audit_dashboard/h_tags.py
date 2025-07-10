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

class HTagsCalculator(BaseKPICalculator):
    """Calculate H tags related KPIs and generate detailed analysis."""
    
    def calculate_kpis(self) -> Dict:
        """Calculate all H tags KPIs with specific filtering logic."""
        total_pages = len(self.df)
        
        # Base filter: Content_Type = 'text/html; charset=UTF-8'
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        html_pages = self.df[html_mask]
        total_html_pages = len(html_pages)
        
        # H1 Tag Analysis
        # 1. All H1 tags: Content_Type = 'text/html; charset=UTF-8' AND H1-1 has value
        h1_mask = html_mask & (
            self.df['H1_1'].notna() & 
            (self.df['H1_1'] != '') &
            (self.df['H1_1'].astype(str).str.strip() != '')
        )
        all_h1_count = int(h1_mask.sum())
        all_h1_percentage = (all_h1_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 2. H1 Missing: Content_Type = 'text/html; charset=UTF-8' AND H1_1 is empty/null
        h1_missing_mask = html_mask & (
            self.df['H1_1'].isna() | 
            (self.df['H1_1'] == '') |
            (self.df['H1_1'].astype(str).str.strip() == '')
        )
        h1_missing_count = int(h1_missing_mask.sum())
        h1_missing_percentage = (h1_missing_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 3. H1 Duplicate: Content_Type = 'text/html; charset=UTF-8' AND H1_1 values are duplicated
        h1_duplicate_mask = html_mask & (
            self.df['H1_1'].notna() & 
            (self.df['H1_1'] != '') &
            (self.df['H1_1'].astype(str).str.strip() != '') &
            self.df['H1_1'].duplicated(keep=False)
        )
        h1_duplicate_count = int(h1_duplicate_mask.sum())
        h1_duplicate_percentage = (h1_duplicate_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 4. H1 Over 70 characters: Content_Type = 'text/html; charset=UTF-8' AND H1_1 Length > 70
        h1_over_70_mask = html_mask & (
            self.df['H1_1_Length'].notna() & 
            (pd.to_numeric(self.df['H1_1_Length'], errors='coerce') > 70)
        )
        h1_over_70_count = int(h1_over_70_mask.sum())
        h1_over_70_percentage = (h1_over_70_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 5. Multiple H1: Content_Type = 'text/html; charset=UTF-8' AND H1_2 has value
        multiple_h1_mask = html_mask & (
            self.df['H1_2'].notna() & 
            (self.df['H1_2'] != '') &
            (self.df['H1_2'].astype(str).str.strip() != '')
        )
        multiple_h1_count = int(multiple_h1_mask.sum())
        multiple_h1_percentage = (multiple_h1_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # H2 Tag Analysis
        # 1. All H2 tags: Content_Type = 'text/html; charset=UTF-8' AND H2_1 has value
        h2_mask = html_mask & (
            self.df['H2_1'].notna() & 
            (self.df['H2_1'] != '') &
            (self.df['H2_1'].astype(str).str.strip() != '')
        )
        all_h2_count = int(h2_mask.sum())
        all_h2_percentage = (all_h2_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 2. H2 Missing: Content_Type = 'text/html; charset=UTF-8' AND H2_1 is empty/null
        h2_missing_mask = html_mask & (
            self.df['H2_1'].isna() | 
            (self.df['H2_1'] == '') |
            (self.df['H2_1'].astype(str).str.strip() == '')
        )
        h2_missing_count = int(h2_missing_mask.sum())
        h2_missing_percentage = (h2_missing_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 3. H2 Duplicate: Content_Type = 'text/html; charset=UTF-8' AND H2_1 values are duplicated
        h2_duplicate_mask = html_mask & (
            self.df['H2_1'].notna() & 
            (self.df['H2_1'] != '') &
            (self.df['H2_1'].astype(str).str.strip() != '') &
            self.df['H2_1'].duplicated(keep=False)
        )
        h2_duplicate_count = int(h2_duplicate_mask.sum())
        h2_duplicate_percentage = (h2_duplicate_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 4. H2 Over 70 characters: Content_Type = 'text/html; charset=UTF-8' AND H2_1 Length > 70
        # h2_over_70_mask = html_mask & (
        #     self.df['H2_1_Length'].notna() & 
        #     (self.df['H2_1_Length'] > 70)
        # )
        # h2_over_70_count = int(h2_over_70_mask.sum())
        # h2_over_70_percentage = (h2_over_70_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # # 5. Multiple H2: Content_Type = 'text/html; charset=UTF-8' AND H2-2 has value
        # multiple_h2_mask = html_mask & (
        #     self.df['H2-2'].notna() & 
        #     (self.df['H2-2'] != '') &
        #     (self.df['H2-2'].astype(str).str.strip() != '')
        # )
        # multiple_h2_count = int(multiple_h2_mask.sum())
        # multiple_h2_percentage = (multiple_h2_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        self.kpis = {
            'h_tags_kpis': {
                    'all_h1': {
                        'count': all_h1_count,
                        'percentage': round(all_h1_percentage, 1)
                    },
                    'h1_missing': {
                        'count': h1_missing_count,
                        'percentage': round(h1_missing_percentage, 1)
                    },
                    'h1_duplicate': {
                        'count': h1_duplicate_count,
                        'percentage': round(h1_duplicate_percentage, 1)
                    },
                    'h1_over_70_chars': {
                        'count': h1_over_70_count,
                        'percentage': round(h1_over_70_percentage, 1)
                    },
                    'multiple_h1': {
                        'count': multiple_h1_count,
                        'percentage': round(multiple_h1_percentage, 1)
                    },
                # },
                # 'h2_analysis': {
                    # 'all_h2': {
                    #     'count': all_h2_count,
                    #     'percentage': round(all_h2_percentage, 1)
                    # },
                    'h2_missing': {
                        'count': h2_missing_count,
                        'percentage': round(h2_missing_percentage, 1)
                    },
                    'h2_duplicate': {
                        'count': h2_duplicate_count,
                        'percentage': round(h2_duplicate_percentage, 1)
                    },
                    # 'h2_over_70_chars': {
                    #     'count': h2_over_70_count,
                    #     'percentage': round(h2_over_70_percentage, 1)
                    # },
                    # 'multiple_h2': {
                    #     'count': multiple_h2_count,
                    #     'percentage': round(multiple_h2_percentage, 1)
                    # }
                }
            }

        
        return self.kpis
    
    def get_all_h1_table(self) -> pd.DataFrame:
        """Get table for all H1 tags."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        h1_mask = html_mask & (
            self.df['H1_1'].notna() & 
            (self.df['H1_1'] != '') &
            (self.df['H1_1'].astype(str).str.strip() != '')
        )
        
        filtered_df = self.df[h1_mask]
        return filtered_df[['Address', 'H1_1', 'H1_1_Length', 'Status_Code', 'Title_1']].copy()
    
    def get_h1_missing_table(self) -> pd.DataFrame:
        """Get table for pages missing H1 tags."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        h1_missing_mask = html_mask & (
            self.df['H1_1'].isna() | 
            (self.df['H1_1'] == '') |
            (self.df['H1_1'].astype(str).str.strip() == '')
        )
        
        filtered_df = self.df[h1_missing_mask]
        return filtered_df[['Address', 'H1_1', 'Status_Code', 'Title_1']].copy()
    
    def get_h1_duplicate_table(self) -> pd.DataFrame:
        """Get table for duplicate H1 tags."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        h1_duplicate_mask = html_mask & (
            self.df['H1_1'].notna() & 
            (self.df['H1_1'] != '') &
            (self.df['H1_1'].astype(str).str.strip() != '') &
            self.df['H1_1'].duplicated(keep=False)
        )
        
        filtered_df = self.df[h1_duplicate_mask]
        return filtered_df[['Address', 'H1_1', 'H1_1_Length', 'Status_Code', 'Title_1']].copy()
    
    def get_h1_over_70_table(self) -> pd.DataFrame:
        """Get table for H1 tags over 70 characters."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        h1_over_70_mask = html_mask & (
            self.df['H1_1_Length'].notna() & 
            (pd.to_numeric(self.df['H1_1_Length'], errors='coerce') > 70 )
        )
        
        filtered_df = self.df[h1_over_70_mask]
        return filtered_df[['Address', 'H1_1', 'H1_1_Length', 'Status_Code', 'Title_1']].copy()
    
    def get_multiple_h1_table(self) -> pd.DataFrame:
        """Get table for pages with multiple H1 tags."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        multiple_h1_mask = html_mask & (
            self.df['H1_2'].notna() & 
            (self.df['H1_2'] != '') &
            (self.df['H1_2'].astype(str).str.strip() != '')
        )
        
        filtered_df = self.df[multiple_h1_mask]
        return filtered_df[['Address', 'H1_1', 'H1_2', 'H1_1_Length', 'H1_2_Length', 'Status_Code', 'Title_1']].copy()
    
    # def get_all_h2_table(self) -> pd.DataFrame:
    #     """Get table for all H2 tags."""
    #     html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
    #     h2_mask = html_mask & (
    #         self.df['H2_1'].notna() & 
    #         (self.df['H2_1'] != '') &
    #         (self.df['H2_1'].astype(str).str.strip() != '')
    #     )
        
    #     filtered_df = self.df[h2_mask]
    #     return filtered_df[['Address', 'H2_1', 'H2_1_Length', 'Status_Code', 'Title_1']].copy()
    
    def get_h2_missing_table(self) -> pd.DataFrame:
        """Get table for pages missing H2 tags."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        h2_missing_mask = html_mask & (
            self.df['H2_1'].isna() | 
            (self.df['H2_1'] == '') |
            (self.df['H2_1'].astype(str).str.strip() == '')
        )
        
        filtered_df = self.df[h2_missing_mask]
        return filtered_df[['Address', 'H2_1', 'Status_Code', 'Title_1']].copy()
    
    def get_h2_duplicate_table(self) -> pd.DataFrame:
        """Get table for duplicate H2 tags."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        h2_duplicate_mask = html_mask & (
            self.df['H2_1'].notna() & 
            (self.df['H2_1'] != '') &
            (self.df['H2_1'].astype(str).str.strip() != '') &
            self.df['H2_1'].duplicated(keep=False)
        )
        
        filtered_df = self.df[h2_duplicate_mask]
        return filtered_df[['Address', 'H2_1', 'H2_1_Length', 'Status_Code', 'Title_1']].copy()
    
    # def get_h2_over_70_table(self) -> pd.DataFrame:
    #     """Get table for H2 tags over 70 characters."""
    #     html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
    #     h2_over_70_mask = html_mask & (
    #         self.df['H2_1_Length'].notna() & 
    #         (self.df['H2_1_Length'] > 70)
    #     )
        
    #     filtered_df = self.df[h2_over_70_mask]
    #     return filtered_df[['Address', 'H2_1', 'H2_1_Length', 'Status_Code', 'Title_1']].copy()
    
    # def get_multiple_h2_table(self) -> pd.DataFrame:
    #     """Get table for pages with multiple H2 tags."""
    #     html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
    #     multiple_h2_mask = html_mask & (
    #         self.df['H2-2'].notna() & 
    #         (self.df['H2-2'] != '') &
    #         (self.df['H2-2'].astype(str).str.strip() != '')
    #     )
        
    #     filtered_df = self.df[multiple_h2_mask]
        # return filtered_df[['Address', 'H2_1', 'H2-2', 'H2_1_Length', 'H2-2_Length', 'Status_Code', 'Title_1']].copy()
    
    def export_h_tags_report(self, filename: str = 'h_tags_report.json') -> Dict:
        """Export detailed H tags report."""
        if not self.kpis:
            self.calculate_kpis()
        
        report = {
            'kpis': self.kpis,
            'tables': {
                'all_h1': self.get_all_h1_table().to_dict('records'),
                'h1_missing': self.get_h1_missing_table().to_dict('records'),
                'h1_duplicate': self.get_h1_duplicate_table().to_dict('records'),
                'h1_over_70_chars': self.get_h1_over_70_table().to_dict('records'),
                'multiple_h1': self.get_multiple_h1_table().to_dict('records'),
                # 'all_h2': self.get_all_h2_table().to_dict('records'),
                'h2_missing': self.get_h2_missing_table().to_dict('records'),
                'h2_duplicate': self.get_h2_duplicate_table().to_dict('records'),
                # 'h2_over_70_chars': self.get_h2_over_70_table().to_dict('records'),
                # 'multiple_h2': self.get_multiple_h2_table().to_dict('records')
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
        
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Transform column names if requested
        if self.transform_column_names:
            if self.transform_column_names:
                final_df.columns = [
                    col.replace(" ", "_")
                    .replace("-", "_")
                    for col in final_df.columns
                ]
        
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
            'tabs_processed': 1 if isinstance(self.raw_data, dict) else len(self.raw_data) if isinstance(self.raw_data, list) else 0,
            'column_names_transformed': self.transform_column_names
        }


def h_tags_kpis_and_table(data):
    """Main function to process data and generate H tags KPIs and tables."""
    
    try:
        # Wrap single data object in list if needed
        if isinstance(data, dict):
            data_process = [data]
        else:
            data_process = data
        
        # Process the data with column transformation enabled by default
        processor = DataProcessor(data_process, transform_column_names=True)
        df = processor.get_dataframe()
        
        if df.empty:
            print("Error: No data to process")
            return None
        
        print("Data Info:")
        print(json.dumps(processor.get_data_info(), indent=2))
        print("\n" + "="*50 + "\n")
        
        # Calculate H Tags KPIs
        h_tags_calc = HTagsCalculator(df)
        h_tags_kpis = h_tags_calc.calculate_kpis()
        
        # Export full report
        full_result = h_tags_calc.export_h_tags_report('h_tags_analysis.json')
        
        return full_result
        
    except Exception as e:
        print(f"Error processing data: {e}")
        return None


# Example usage and testing
# if __name__ == "__main__":
#     # Test with sample data
#     sample_data = {
#         'values': [
#             ['Address', 'Content Type', 'H1-1', 'H1-1 Length', 'H1_2', 'H1_2 Length', 'H2_1', 'H2_1 Length', 'H2-2', 'H2-2 Length', 'Status Code', 'Status', 'Title 1'],
#             ['https://example.com', 'text/html; charset=UTF-8', 'Welcome to Example', 18, '', '', 'About Us', 8, 'Our Services', 12, '200', 'OK', 'Home Page'],
#             ['https://example.com/page1', 'text/html; charset=UTF-8', '', '', '', '', '', '', '', '', '200', 'OK', 'Page 1'],
#             ['https://example.com/page2', 'text/html; charset=UTF-8', 'Welcome to Example', 18, '', '', 'Our Products', 12, '', '', '200', 'OK', 'Page 2'],
#             ['https://example.com/page3', 'text/html; charset=UTF-8', 'This is a very long H1 tag that exceeds seventy characters and should be flagged', 85, '', '', 'Long H2 tag that also exceeds the seventy character limit and should be detected', 85, '', '', '200', 'OK', 'Page 3'],
#             ['https://example.com/page4', 'text/html; charset=UTF-8', 'Multiple H1 First', 18, 'Multiple H1 Second', 19, 'H2 Content', 10, 'Another H2', 11, '200', 'OK', 'Page 4'],
#             ['https://example.com/page5', 'application/pdf', 'PDF H1', 7, '', '', '', '', '', '', '200', 'OK', 'PDF Page']
#         ]
#     }
    
#     result = h_tags_kpis_and_table(sample_data)
#     if result:
#         print("H Tags KPIs calculated successfully!")
#         print(json.dumps(result['kpis'], indent=2))
#         print("\nSample table data:")
#         print(f"H1 Missing URLs: {len(result['tables']['h1_missing'])}")
#         print(f"H1 Duplicate URLs: {len(result['tables']['h1_duplicate'])}")
#         print(f"H1 Over 70 chars URLs: {len(result['tables']['h1_over_70_chars'])}")