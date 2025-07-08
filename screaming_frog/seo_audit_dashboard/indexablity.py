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

class IndexabilityCalculator(BaseKPICalculator):
    """Calculate indexability-related KPIs and generate detailed analysis."""
    
    def calculate_kpis(self) -> Dict:
        """Calculate all indexability KPIs with specific filtering logic."""
        total_pages = len(self.df)
        
        # Base filter: Content Type = 'text/html; charset=UTF-8'
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        html_pages = self.df[html_mask]
        total_html_pages = len(html_pages)
        
        # 1. Indexable URLs: Content Type = 'text/html; charset=UTF-8' AND Indexability = 'Indexable'
        indexable_mask = html_mask & (self.df['Indexability'] == 'Indexable')
        indexable_count = int(indexable_mask.sum())
        indexable_percentage = (indexable_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 2. Non-indexable URLs: Content Type = 'text/html; charset=UTF-8' AND Indexability = 'Non-Indexable'
        non_indexable_mask = html_mask & (self.df['Indexability'] == 'Non-Indexable')
        non_indexable_count = int(non_indexable_mask.sum())
        non_indexable_percentage = (non_indexable_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 3. URLs with Meta Noindex: Content Type = 'text/html; charset=UTF-8' AND 
        # (Meta Robots 1 contains 'noindex' OR X-Robots-Tag 1 contains 'noindex')
        meta_robots_noindex = self.df['Meta Robots 1'].str.contains('noindex', case=False, na=False)
        x_robots_noindex = self.df['X-Robots-Tag 1'].str.contains('noindex', case=False, na=False)
        meta_noindex_mask = html_mask & (meta_robots_noindex | x_robots_noindex)
        meta_noindex_count = int(meta_noindex_mask.sum())
        meta_noindex_percentage = (meta_noindex_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 4. Blocked by robots.txt
        blocked_by_robots_mask = html_mask & self.df['Indexability Status'].str.contains('Blocked by robots.txt', case=False, na=False)
        blocked_by_robots_count = int(blocked_by_robots_mask.sum())
        blocked_by_robots_percentage = (blocked_by_robots_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # Canonical tag analysis
        # 1. Contains Canonical Tag: Has a value in the canonical column
        contains_canonical_mask = html_mask & (
            self.df['Canonical Link Element 1'].notna() & 
            (self.df['Canonical Link Element 1'] != '') &
            (self.df['Canonical Link Element 1'].astype(str).str.strip() != '')
        )
        contains_canonical_count = int(contains_canonical_mask.sum())
        contains_canonical_percentage = (contains_canonical_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 2. Missing Canonical Tag: Empty or null value in canonical column
        missing_canonical_mask = html_mask & (
            self.df['Canonical Link Element 1'].isna() | 
            (self.df['Canonical Link Element 1'] == '') |
            (self.df['Canonical Link Element 1'].astype(str).str.strip() == '')
        )
        missing_canonical_count = int(missing_canonical_mask.sum())
        missing_canonical_percentage = (missing_canonical_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 3. Self-Referencing Canonical: Canonical URL matches the Address
        self_referencing_mask = html_mask & (
            self.df['Canonical Link Element 1'].notna() & 
            (self.df['Canonical Link Element 1'] != '') &
            (self.df['Canonical Link Element 1'] == self.df['Address'])
        )
        self_referencing_count = int(self_referencing_mask.sum())
        self_referencing_percentage = (self_referencing_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        # 4. Canonicalized to Different URL: Canonical URL is different from Address
        canonicalized_different_mask = html_mask & (
            self.df['Canonical Link Element 1'].notna() & 
            (self.df['Canonical Link Element 1'] != '') &
            (self.df['Canonical Link Element 1'].astype(str).str.strip() != '') &
            (self.df['Canonical Link Element 1'] != self.df['Address'])
        )
        canonicalized_different_count = int(canonicalized_different_mask.sum())
        canonicalized_different_percentage = (canonicalized_different_count / total_html_pages * 100) if total_html_pages > 0 else 0
        
        self.kpis = {
            'indexability_kpis': {
                # 'total_pages': total_pages,
                # 'total_html_pages': total_html_pages,
                'indexable': {
                    'count': indexable_count,
                    'percentage': round(indexable_percentage, 1)
                },
                'non_indexable': {
                    'count': non_indexable_count,
                    'percentage': round(non_indexable_percentage, 1)
                },
                'meta_noindex': {
                    'count': meta_noindex_count,
                    'percentage': round(meta_noindex_percentage, 1)
                },
                'blocked_by_robots': {
                    'count': blocked_by_robots_count,
                    'percentage': round(blocked_by_robots_percentage, 1)
                },
                'contains_canonical': {
                    'count': contains_canonical_count,
                    'percentage': round(contains_canonical_percentage, 1)
                },
                'missing_canonical': {
                    'count': missing_canonical_count,
                    'percentage': round(missing_canonical_percentage, 1)
                },
                'self_referencing': {
                    'count': self_referencing_count,
                    'percentage': round(self_referencing_percentage, 1)
                },
                'canonicalized_different': {
                    'count': canonicalized_different_count,
                    'percentage': round(canonicalized_different_percentage, 1)
                }
            }
        }
        
        return self.kpis
    
    def get_indexable_urls_table(self) -> pd.DataFrame:
        """Get table for indexable URLs with specific columns."""
        # Filter: Content Type = 'text/html; charset=UTF-8' AND Indexability = 'Indexable'
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        indexable_mask = html_mask & (self.df['Indexability'] == 'Indexable')
        
        filtered_df = self.df[indexable_mask]
        
        # Return specific columns: Address / Indexability / Indexability Status / Title 1
        return filtered_df[['Address', 'Indexability', 'Indexability Status', 'Title 1']].copy()
    
    def get_non_indexable_urls_table(self) -> pd.DataFrame:
        """Get table for non-indexable URLs with specific columns."""
        # Filter: Content Type = 'text/html; charset=UTF-8' AND Indexability = 'Non-Indexable'
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        non_indexable_mask = html_mask & (self.df['Indexability'] == 'Non-Indexable')
        
        filtered_df = self.df[non_indexable_mask]
        
        # Return specific columns: Address / Indexability / Indexability Status / Title 1
        return filtered_df[['Address', 'Indexability', 'Indexability Status', 'Title 1']].copy()
    
    def get_meta_noindex_urls_table(self) -> pd.DataFrame:
        """Get table for URLs with meta noindex."""
        # Filter: Content Type = 'text/html; charset=UTF-8' AND 
        # (Meta Robots 1 contains 'noindex' OR X-Robots-Tag 1 contains 'noindex')
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        meta_robots_noindex = self.df['Meta Robots 1'].str.contains('noindex', case=False, na=False)
        x_robots_noindex = self.df['X-Robots-Tag 1'].str.contains('noindex', case=False, na=False)
        meta_noindex_mask = html_mask & (meta_robots_noindex | x_robots_noindex)
        
        filtered_df = self.df[meta_noindex_mask]
        
        # Return specific columns: Address / Status Code / Status / Meta Robots 1 / X-Robots-Tag 1 / Title 1
        return filtered_df[['Address', 'Status Code', 'Status', 'Meta Robots 1', 'X-Robots-Tag 1', 'Title 1']].copy()
    
    def get_blocked_by_robots_table(self) -> pd.DataFrame:
        """Get table for URLs blocked by robots.txt."""
        # Filter: Content Type = 'text/html; charset=UTF-8' AND Indexability Status contains 'Blocked by robots.txt'
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        blocked_mask = html_mask & self.df['Indexability Status'].str.contains('Blocked by robots.txt', case=False, na=False)
        
        filtered_df = self.df[blocked_mask]
        
        # Return specific columns: Address / Status Code / Status / Indexability Status / Title 1
        return filtered_df[['Address', 'Status Code', 'Status', 'Indexability Status', 'Title 1']].copy()
    
    def get_contains_canonical_table(self) -> pd.DataFrame:
        """Get table for URLs that contain canonical tags."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        contains_canonical_mask = html_mask & (
            self.df['Canonical Link Element 1'].notna() & 
            (self.df['Canonical Link Element 1'] != '') &
            (self.df['Canonical Link Element 1'].astype(str).str.strip() != '')
        )
        
        filtered_df = self.df[contains_canonical_mask]
        
        return filtered_df[['Address', 'Canonical Link Element 1', 'Title 1']].copy()
    
    def get_missing_canonical_table(self) -> pd.DataFrame:
        """Get table for URLs missing canonical tags."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        missing_canonical_mask = html_mask & (
            self.df['Canonical Link Element 1'].isna() | 
            (self.df['Canonical Link Element 1'] == '') |
            (self.df['Canonical Link Element 1'].astype(str).str.strip() == '')
        )
        
        filtered_df = self.df[missing_canonical_mask]
        
        return filtered_df[['Address', 'Canonical Link Element 1', 'Title 1']].copy()
    
    def get_self_referencing_table(self) -> pd.DataFrame:
        """Get table for URLs with self-referencing canonical tags."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        self_referencing_mask = html_mask & (
            self.df['Canonical Link Element 1'].notna() & 
            (self.df['Canonical Link Element 1'] != '') &
            (self.df['Canonical Link Element 1'] == self.df['Address'])
        )
        
        filtered_df = self.df[self_referencing_mask]
        
        return filtered_df[['Address', 'Canonical Link Element 1', 'Title 1']].copy()
    
    def get_canonicalized_different_table(self) -> pd.DataFrame:
        """Get table for URLs canonicalized to different URLs."""
        html_mask = self.df['Content Type'] == 'text/html; charset=UTF-8'
        canonicalized_different_mask = html_mask & (
            self.df['Canonical Link Element 1'].notna() & 
            (self.df['Canonical Link Element 1'] != '') &
            (self.df['Canonical Link Element 1'].astype(str).str.strip() != '') &
            (self.df['Canonical Link Element 1'] != self.df['Address'])
        )
        
        filtered_df = self.df[canonicalized_different_mask]
        
        return filtered_df[['Address', 'Canonical Link Element 1', 'Title 1']].copy()
    
    def export_indexability_report(self, filename: str = 'indexability_report.json') -> Dict:
        """Export detailed indexability report."""
        if not self.kpis:
            self.calculate_kpis()
        
        report = {
            'kpis': self.kpis,
            'tables': {
                'indexable_urls': self.get_indexable_urls_table().to_dict('records'),
                'non_indexable_urls': self.get_non_indexable_urls_table().to_dict('records'),
                'meta_noindex_urls': self.get_meta_noindex_urls_table().to_dict('records'),
                'blocked_by_robots_urls': self.get_blocked_by_robots_table().to_dict('records'),
                'contains_canonical': self.get_contains_canonical_table().to_dict('records'),
                'missing_canonical': self.get_missing_canonical_table().to_dict('records'),
                'self_referencing': self.get_self_referencing_table().to_dict('records'),
                'canonicalized_different': self.get_canonicalized_different_table().to_dict('records')
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


def indexability_kpis_and_table(data):
    """Main function to process data and generate indexability KPIs and tables."""
    
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
        
        # Calculate Indexability KPIs
        indexability_calc = IndexabilityCalculator(df)
        indexability_kpis = indexability_calc.calculate_kpis()
        
        # # Show indexability tables
        # print("=== INDEXABILITY TABLES ===\n")
        
        # # 1. Indexable URLs Table
        # indexable_table = indexability_calc.get_indexable_urls_table()
        # print(f"1. INDEXABLE URLs ({len(indexable_table)} items):")
        # print("   Columns: Address / Indexability / Indexability Status / Title 1")
        # if not indexable_table.empty:
        #     print(indexable_table.head(3).to_string(index=False))
        # print()
        
        # # 2. Non-Indexable URLs Table
        # non_indexable_table = indexability_calc.get_non_indexable_urls_table()
        # print(f"2. NON-INDEXABLE URLs ({len(non_indexable_table)} items):")
        # print("   Columns: Address / Indexability / Indexability Status / Title 1")
        # if not non_indexable_table.empty:
        #     print(non_indexable_table.head(3).to_string(index=False))
        # print()
        
        # # 3. Meta Noindex URLs Table
        # meta_noindex_table = indexability_calc.get_meta_noindex_urls_table()
        # print(f"3. META NOINDEX URLs ({len(meta_noindex_table)} items):")
        # print("   Columns: Address / Status Code / Status / Meta Robots 1 / X-Robots-Tag 1 / Title 1")
        # if not meta_noindex_table.empty:
        #     print(meta_noindex_table.head(3).to_string(index=False))
        # print()
        
        # # 4. Blocked by Robots URLs Table
        # blocked_table = indexability_calc.get_blocked_by_robots_table()
        # print(f"4. BLOCKED BY ROBOTS URLs ({len(blocked_table)} items):")
        # print("   Columns: Address / Status Code / Status / Indexability Status / Title 1")
        # if not blocked_table.empty:
        #     print(blocked_table.head(3).to_string(index=False))
        # print("\n" + "="*50 + "\n")
        
        # Export full report
        full_result = indexability_calc.export_indexability_report('indexability_analysis.json')
        
        return full_result
        
    except Exception as e:
        print(f"Error processing data: {e}")
        return None


# Example usage
# if __name__ == "__main__":
#     # Test with sample data
#     sample_data = {
#         'values': [
#             ['Address', 'Content Type', 'Indexability', 'Indexability Status', 'Title 1', 'Meta Robots 1', 'X-Robots-Tag 1', 'Canonical Link Element 1', 'Status Code', 'Status'],
#             ['https://example.com', 'text/html; charset=UTF-8', 'Indexable', 'Indexable', 'Home Page', '', '', 'https://example.com', '200', 'OK'],
#             ['https://example.com/page1', 'text/html; charset=UTF-8', 'Non-Indexable', 'Blocked by robots.txt', 'Page 1', '', '', '', '200', 'OK'],
#             ['https://example.com/page2', 'text/html; charset=UTF-8', 'Non-Indexable', 'Meta Noindex', 'Page 2', 'noindex', '', 'https://example.com/page2', '200', 'OK']
#         ]
#     }
    
#     result = indexability_kpis_and_table(sample_data)
#     if result:
#         print("KPIs calculated successfully!")
#         print(json.dumps(result['kpis'], indent=2))