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

class StatusCodeCalculator(BaseKPICalculator):
    """Calculate status code related KPIs and generate detailed analysis."""
    
    def calculate_kpis(self) -> Dict:
        """Calculate all status code KPIs with specific filtering logic."""
        total_pages = len(self.df)
        
        # Base filter: Content Type = 'text/html; charset=UTF-8'
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        html_pages = self.df[html_mask]
        total_html_pages = len(html_pages)
        
        # 1. 200 Response: Status Code = 200
        response_200_mask = html_mask & (self.df['Status_Code'] == "200")
        response_200_count = int(response_200_mask.sum())
        response_200_percentage = (response_200_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 2. 3xx Response: Status Code starts with 3 OR Indexability Status = 'Redirected'
        response_3xx_mask = html_mask & (
            (self.df['Status_Code'].astype(str).str.startswith('3', na=False)) |
            (self.df['Indexability_Status'].str.contains('Redirected', case=False, na=False))
        )
        response_3xx_count = int(response_3xx_mask.sum())
        response_3xx_percentage = (response_3xx_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 3. 4xx Response: Status Code starts with 4 OR Indexability Status = 'Client Error'
        response_4xx_mask = html_mask & (
            (self.df['Status_Code'].astype(str).str.startswith('4', na=False)) |
            (self.df['Indexability_Status'].str.contains('Client Error', case=False, na=False))
        )
        response_4xx_count = int(response_4xx_mask.sum())
        response_4xx_percentage = (response_4xx_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 4. 5xx Response: Status Code starts with 5 OR Indexability Status = 'Server Error'
        response_5xx_mask = html_mask & (
            (self.df['Status_Code'].astype(str).str.startswith('5', na=False)) |
            (self.df['Indexability_Status'].str.contains('Server Error', case=False, na=False))
        )
        response_5xx_count = int(response_5xx_mask.sum())
        response_5xx_percentage = (response_5xx_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # Additional analysis - Redirect Loop and Redirect Chain
        redirect_loop_mask = html_mask & (
            self.df['Indexability_Status'].str.contains('Redirect Loop', case=False, na=False)
        )
        redirect_loop_count = int(redirect_loop_mask.sum())
        redirect_loop_percentage = (redirect_loop_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        redirect_chain_mask = html_mask & (
            self.df['Indexability_Status'].str.contains('Redirect Chain', case=False, na=False)
        )
        redirect_chain_count = int(redirect_chain_mask.sum())
        redirect_chain_percentage = (redirect_chain_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        self.kpis = {
            'status_code_kpis': {
                # 'total_pages': total_pages,
                # 'total_html_pages': total_html_pages,
                'response_200': {
                    'count': response_200_count,
                    'percentage': round(response_200_percentage, 1)
                },
                'response_3xx': {
                    'count': response_3xx_count,
                    'percentage': round(response_3xx_percentage, 1)
                },
                'response_4xx': {
                    'count': response_4xx_count,
                    'percentage': round(response_4xx_percentage, 1)
                },
                'response_5xx': {
                    'count': response_5xx_count,
                    'percentage': round(response_5xx_percentage, 1)
                },
                'redirect_loop': {
                    'count': redirect_loop_count,
                    'percentage': round(redirect_loop_percentage, 1)
                },
                'redirect_chain': {
                    'count': redirect_chain_count,
                    'percentage': round(redirect_chain_percentage, 1)
                }
            }
        }
        
        return self.kpis
    
    def get_200_response_table(self) -> pd.DataFrame:
        """Get table for 200 response URLs."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        response_200_mask = html_mask & (self.df['Status_Code'] == '200')
        
        filtered_df = self.df[response_200_mask]
        
        # Return specific columns: Address, Status Code, Status, Title 1
        return filtered_df[['Address', 'Status_Code', 'Status','Indexability_Status', 'Title_1']].copy()
    
    def get_3xx_response_table(self) -> pd.DataFrame:
        """Get table for 3xx response URLs."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        response_3xx_mask = html_mask & (
            (self.df['Status_Code'].astype(str).str.startswith('3', na=False)) |
            (self.df['Indexability_Status'].str.contains('Redirected', case=False, na=False))
        )
        
        filtered_df = self.df[response_3xx_mask]
        
        # Return specific columns: Address, Status Code, Status, Indexability Status, Title 1
        return filtered_df[['Address', 'Status_Code', 'Status', 'Indexability_Status', 'Title_1']].copy()
    
    def get_4xx_response_table(self) -> pd.DataFrame:
        """Get table for 4xx response URLs."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        response_4xx_mask = html_mask & (
            (self.df['Status_Code'].astype(str).str.startswith('4', na=False)) |
            (self.df['Indexability_Status'].str.contains('Client Error', case=False, na=False))
        )
        
        filtered_df = self.df[response_4xx_mask]
        
        # Return specific columns: Address, Status Code, Status, Indexability Status, Title 1
        return filtered_df[['Address', 'Status_Code', 'Status', 'Indexability_Status', 'Title_1']].copy()
    
    def get_5xx_response_table(self) -> pd.DataFrame:
        """Get table for 5xx response URLs."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        response_5xx_mask = html_mask & (
            (self.df['Status_Code'].astype(str).str.startswith('5', na=False)) |
            (self.df['Indexability_Status'].str.contains('Server Error', case=False, na=False))
        )
        
        filtered_df = self.df[response_5xx_mask]
        
        # Return specific columns: Address, Status Code, Status, Indexability Status, Title 1
        return filtered_df[['Address', 'Status_Code', 'Status', 'Indexability_Status', 'Title_1']].copy()
    
    def get_redirect_loop_table(self) -> pd.DataFrame:
        """Get table for redirect loop URLs."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        redirect_loop_mask = html_mask & (
            self.df['Indexability_Status'].str.contains('Redirect Loop', case=False, na=False)
        )
        
        filtered_df = self.df[redirect_loop_mask]
        
        # Return specific columns: Address, Status Code, Status, Indexability Status, Title 1
        return filtered_df[['Address', 'Status_Code', 'Status', 'Indexability_Status', 'Title_1']].copy()
    
    def get_redirect_chain_table(self) -> pd.DataFrame:
        """Get table for redirect chain URLs."""
        html_mask = self.df['Content_Type'] == 'text/html; charset=UTF-8'
        redirect_chain_mask = html_mask & (
            self.df['Indexability_Status'].str.contains('Redirect Chain', case=False, na=False)
        )
        
        filtered_df = self.df[redirect_chain_mask]
        
        # Return specific columns: Address, Status Code, Status, Indexability Status, Title 1
        return filtered_df[['Address', 'Status_Code', 'Status', 'Indexability_Status', 'Title_1']].copy()
    
    def export_status_code_report(self, filename: str = 'status_code_report.json') -> Dict:
        """Export detailed status code report."""
        if not self.kpis:
            self.calculate_kpis()
        
        report = {
            'kpis': self.kpis,
            'tables': {
                'response_200': self.get_200_response_table().to_dict('records'),
                'response_3xx': self.get_3xx_response_table().to_dict('records'),
                'response_4xx': self.get_4xx_response_table().to_dict('records'),
                'response_5xx': self.get_5xx_response_table().to_dict('records'),
                'redirect_loop': self.get_redirect_loop_table().to_dict('records'),
                'redirect_chain': self.get_redirect_chain_table().to_dict('records')
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


def status_code_kpis_and_table(data):
    """Main function to process data and generate status code KPIs and tables."""
    
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
        
        # Calculate Status Code KPIs
        status_code_calc = StatusCodeCalculator(df)
        status_code_kpis = status_code_calc.calculate_kpis()
        
        # Export full report
        full_result = status_code_calc.export_status_code_report('status_code_analysis.json')
        
        return full_result
        
    except Exception as e:
        print(f"Error processing data: {e}")
        return None


# Example usage
# if __name__ == "__main__":
#     # Test with sample data
#     sample_data = {
#         'values': [
#             ['Address', 'Content Type', 'Status Code', 'Status', 'Indexability Status', 'Title 1'],
#             ['https://example.com', 'text/html; charset=UTF-8', 200, 'OK', 'Indexable', 'Home Page'],
#             ['https://example.com/page1', 'text/html; charset=UTF-8', 301, 'Moved Permanently', 'Redirected', 'Page 1'],
#             ['https://example.com/page2', 'text/html; charset=UTF-8', 404, 'Not Found', 'Client Error', 'Page 2'],
#             ['https://example.com/page3', 'text/html; charset=UTF-8', 500, 'Internal Server Error', 'Server Error', 'Page 3'],
#             ['https://example.com/loop', 'text/html; charset=UTF-8', 301, 'Moved Permanently', 'Redirect Loop', 'Loop Page'],
#             ['https://example.com/chain', 'text/html; charset=UTF-8', 302, 'Found', 'Redirect Chain', 'Chain Page']
#         ]
#     }
    
#     # Test Status Code KPIs
#     print("=== STATUS CODE KPIs ===")
#     result = status_code_kpis_and_table(sample_data)
#     if result:
#         print("Status Code KPIs calculated successfully!")
#         print(json.dumps(result['kpis'], indent=2))
        
#         # Show sample tables
#         print("\n=== SAMPLE TABLES ===")
#         for table_name, table_data in result['tables'].items():
#             print(f"\n{table_name.upper()}: {len(table_data)} items")
#             if table_data:
#                 print(f"Sample: {table_data[0]}")
#     else:
#         print("Failed to calculate KPIs")