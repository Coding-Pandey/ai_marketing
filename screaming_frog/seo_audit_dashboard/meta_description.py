
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

class MetaDescriptionCalculator(BaseKPICalculator):
    """Calculate meta description-related KPIs and generate detailed analysis."""
    
    def calculate_kpis(self) -> Dict:
        """Calculate all meta description KPIs with specific filtering logic."""
        # Base filter: Content Type = 'text/html; charset=UTF-8'
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        html_pages = self.df[html_mask]
        total_html_pages = len(html_pages)
        
        # 1. All Meta Descriptions: Count all pages with any meta description content
        all_meta_desc_mask = html_mask & (
            self.df['Meta Description 1'].notna() & 
            (self.df['Meta Description 1'] != '') &
            (self.df['Meta Description 1'].astype(str).str.strip() != '')
        )
        all_meta_desc_count = int(all_meta_desc_mask.sum())
        all_meta_desc_percentage = (all_meta_desc_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 2. Missing Meta Descriptions: Null/empty values in Meta Description 1
        missing_meta_desc_mask = html_mask & (
            self.df['Meta Description 1'].isna() | 
            (self.df['Meta Description 1'] == '') |
            (self.df['Meta Description 1'].astype(str).str.strip() == '')
        )
        missing_meta_desc_count = int(missing_meta_desc_mask.sum())
        missing_meta_desc_percentage = (missing_meta_desc_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 3. Duplicate Meta Descriptions: Same meta description text appears multiple times
        # First get non-empty meta descriptions
        non_empty_meta_desc = html_pages[
            html_pages['Meta Description 1'].notna() & 
            (html_pages['Meta Description 1'] != '') &
            (html_pages['Meta Description 1'].astype(str).str.strip() != '')
        ]
        
        # Find duplicates
        duplicate_meta_desc_mask = html_mask & (
            self.df['Meta Description 1'].notna() & 
            (self.df['Meta Description 1'] != '') &
            (self.df['Meta Description 1'].astype(str).str.strip() != '') &
            self.df['Meta Description 1'].duplicated(keep=False)
        )
        duplicate_meta_desc_count = int(duplicate_meta_desc_mask.sum())
        duplicate_meta_desc_percentage = (duplicate_meta_desc_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 4. Over 160 Characters: Use Meta Description 1 Length > 160
        over_160_mask = html_mask & (
            self.df['Meta Description 1 Length'].notna() & 
            (self.df['Meta Description 1 Length'] > "160")
        )
        over_160_count = int(over_160_mask.sum())
        over_160_percentage = (over_160_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 5. Below 70 Characters: Use Meta Description 1 Length < 70
        below_70_mask = html_mask & (
            self.df['Meta Description 1 Length'].notna() & 
            (self.df['Meta Description 1 Length'] < '70') &
            (self.df['Meta Description 1 Length'] > 0)  # Exclude empty descriptions
        )
        below_70_count = int(below_70_mask.sum())
        below_70_percentage = (below_70_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 6. Multiple Meta Descriptions: Check if there are multiple meta description tags
        # This would require checking if Meta Description 2, 3, etc. exist and have values
        multiple_meta_desc_mask = html_mask & (
            (self.df.get('Meta Description 2', pd.Series()).notna() & 
             (self.df.get('Meta Description 2', pd.Series()) != '')) |
            (self.df.get('Meta Description 3', pd.Series()).notna() & 
             (self.df.get('Meta Description 3', pd.Series()) != ''))
        )
        multiple_meta_desc_count = int(multiple_meta_desc_mask.sum())
        multiple_meta_desc_percentage = (multiple_meta_desc_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        self.kpis = {
            'meta_description_kpis': {
                'all_meta_descriptions': {
                    'count': all_meta_desc_count,
                    'percentage': round(all_meta_desc_percentage, 1)
                },
                'missing_meta_descriptions': {
                    'count': missing_meta_desc_count,
                    'percentage': round(missing_meta_desc_percentage, 1)
                },
                'duplicate_meta_descriptions': {
                    'count': duplicate_meta_desc_count,
                    'percentage': round(duplicate_meta_desc_percentage, 1)
                },
                'over_160_characters': {
                    'count': over_160_count,
                    'percentage': round(over_160_percentage, 1)
                },
                'below_70_characters': {
                    'count': below_70_count,
                    'percentage': round(below_70_percentage, 1)
                },
                'multiple_meta_descriptions': {
                    'count': multiple_meta_desc_count,
                    'percentage': round(multiple_meta_desc_percentage, 1)
                }
            }
        }
        
        return self.kpis
    
    def get_missing_meta_descriptions_table(self) -> pd.DataFrame:
        """Get table for URLs missing meta descriptions."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        missing_meta_desc_mask = html_mask & (
            self.df['Meta Description 1'].isna() | 
            (self.df['Meta Description 1'] == '') |
            (self.df['Meta Description 1'].astype(str).str.strip() == '')
        )
        
        filtered_df = self.df[missing_meta_desc_mask]
        
        return filtered_df[['Address', 'Meta Description 1', 'Title 1']].copy()
    
    def get_duplicate_meta_descriptions_table(self) -> pd.DataFrame:
        """Get table for URLs with duplicate meta descriptions."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        duplicate_meta_desc_mask = html_mask & (
            self.df['Meta Description 1'].notna() & 
            (self.df['Meta Description 1'] != '') &
            (self.df['Meta Description 1'].astype(str).str.strip() != '') &
            self.df['Meta Description 1'].duplicated(keep=False)
        )
        
        filtered_df = self.df[duplicate_meta_desc_mask]
        
        return filtered_df[['Address', 'Meta Description 1', 'Meta Description 1 Length', 'Title 1']].copy()
    
    def get_over_160_characters_table(self) -> pd.DataFrame:
        """Get table for URLs with meta descriptions over 160 characters."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        over_160_mask = html_mask & (
            self.df['Meta Description 1 Length'].notna() & 
            (self.df['Meta Description 1 Length'] > 160)
        )
        
        filtered_df = self.df[over_160_mask]
        
        return filtered_df[['Address', 'Meta Description 1', 'Meta Description 1 Length', 'Meta Description 1 Pixel Width', 'Title 1']].copy()
    
    def get_below_70_characters_table(self) -> pd.DataFrame:
        """Get table for URLs with meta descriptions below 70 characters."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        below_70_mask = html_mask & (
            self.df['Meta Description 1 Length'].notna() & 
            (self.df['Meta Description 1 Length'] < 70) &
            (self.df['Meta Description 1 Length'] > 0)  # Exclude empty descriptions
        )
        
        filtered_df = self.df[below_70_mask]
        
        return filtered_df[['Address', 'Meta Description 1', 'Meta Description 1 Length', 'Meta Description 1 Pixel Width', 'Title 1']].copy()
    
    def get_multiple_meta_descriptions_table(self) -> pd.DataFrame:
        """Get table for URLs with multiple meta descriptions."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        multiple_meta_desc_mask = html_mask & (
            (self.df.get('Meta Description 2', pd.Series()).notna() & 
             (self.df.get('Meta Description 2', pd.Series()) != '')) |
            (self.df.get('Meta Description 3', pd.Series()).notna() & 
             (self.df.get('Meta Description 3', pd.Series()) != ''))
        )
        
        filtered_df = self.df[multiple_meta_desc_mask]
        
        # Include available meta description columns
        columns = ['Address', 'Meta Description 1', 'Title 1']
        if 'Meta Description 2' in self.df.columns:
            columns.insert(-1, 'Meta Description 2')
        if 'Meta Description 3' in self.df.columns:
            columns.insert(-1, 'Meta Description 3')
        
        return filtered_df[columns].copy()
    
    def export_meta_description_report(self, filename: str = 'meta_description_report.json') -> Dict:
        """Export detailed meta description report."""
        if not self.kpis:
            self.calculate_kpis()
        
        report = {
            'kpis': self.kpis,
            'tables': {
                'missing_meta_descriptions': self.get_missing_meta_descriptions_table().to_dict('records'),
                'duplicate_meta_descriptions': self.get_duplicate_meta_descriptions_table().to_dict('records'),
                'over_160_characters': self.get_over_160_characters_table().to_dict('records'),
                'below_70_characters': self.get_below_70_characters_table().to_dict('records'),
                'multiple_meta_descriptions': self.get_multiple_meta_descriptions_table().to_dict('records')
            }
        }
        
        # Optional: Save to file
        # try:
        #     with open(filename, 'w') as f:
        #         json.dump(report, f, indent=2)
        #     print(f"Report saved to {filename}")
        # except Exception as e:
        #     print(f"Could not save file: {e}")
        
        return report


class DataProcessor:
    """Process crawl data and initialize it for KPI calculations."""
    
    def __init__(self, data: Union[str, dict, List[dict]]):
        self.raw_data = data
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
        
        return pd.concat(all_data, ignore_index=True)
    
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


def meta_description_kpis_and_tables(data):
    """Main function to process data and generate meta description KPIs and tables."""
    
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
        
        # Calculate Meta Description KPIs
        meta_desc_calc = MetaDescriptionCalculator(df)
        meta_desc_kpis = meta_desc_calc.calculate_kpis()
        
        # Export full report
        full_result = meta_desc_calc.export_meta_description_report('meta_description_analysis.json')
        
        return full_result
        
    except Exception as e:
        print(f"Error processing data: {e}")
        return None


# Example usage
# if __name__ == "__main__":
#     # Test with sample data
#     sample_data = {
#         'values': [
#             ['Address', 'Content Type', 'Meta Description 1', 'Meta Description 1 Length', 'Meta Description 1 Pixel Width', 'Title 1'],
#             ['https://example.com', 'text/html; charset=UTF-8', 'This is a sample meta description for the home page', 52, 320, 'Home Page'],
#             ['https://example.com/page1', 'text/html; charset=UTF-8', '', 0, 0, 'Page 1'],
#             ['https://example.com/page2', 'text/html; charset=UTF-8', 'This is a sample meta description for the home page', 52, 320, 'Page 2'],
#             ['https://example.com/page3', 'text/html; charset=UTF-8', 'This is a very long meta description that exceeds the recommended 160 character limit and should be flagged as too long for optimal search engine display', 170, 1100, 'Page 3'],
#             ['https://example.com/page4', 'text/html; charset=UTF-8', 'Short', 5, 30, 'Page 4']
#         ]
#     }
    
#     result = meta_description_kpis_and_tables(sample_data)
#     if result:
#         print("Meta Description KPIs calculated successfully!")
#         print(json.dumps(result['kpis'], indent=2))