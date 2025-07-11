# sheets_service.py - Modified for direct database storage
import os
import subprocess
import pandas as pd
import tempfile
import uuid
from datetime import datetime
from typing import List, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from screaming_frog.seo_audit_dashboard.indexablity import indexability_kpis_and_table
from screaming_frog.seo_audit_dashboard.status_code import status_code_kpis_and_table
from screaming_frog.seo_audit_dashboard.page_title import page_title_kpis_and_table
from screaming_frog.seo_audit_dashboard.meta_description import meta_description_kpis_and_tables
from screaming_frog.seo_audit_dashboard.h_tags import h_tags_kpis_and_table
from auth.models import Sf_crawl_data 


class ScreamingFrogCrawlService:
    """Service for crawling with Screaming Frog and saving directly to database"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def crawl_and_save_to_db(
        self,
        domain: str,
        user_id: int,
        export_tabs: List[str] = None
    ) -> Dict:
        """
        Crawl domain with Screaming Frog and save results directly to database.
        
        :param domain: Domain to crawl
        :param user_id: User ID for database record
        :param export_tabs: List of Screaming Frog tab names
        :return: Dictionary with crawl results and database record info
        """
        if export_tabs is None:
            export_tabs = ["Internal:All"]
        
        if not export_tabs:
            raise HTTPException(400, "At least one export tab must be specified.")

        # Generate unique UUID for this crawl batch
        batch_uuid = uuid.uuid4().hex
        
        # Prepare comma-separated tabs for Screaming Frog
        tabs_arg = ",".join(export_tabs)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Using temporary directory: {temp_dir}")
            try:
                # Single crawl for all tabs
                self._run_screaming_frog_crawl(domain, temp_dir, tabs_arg)
                
                # Process the main "Internal:All" CSV for KPI calculation
                internal_all_csv = os.path.join(temp_dir, "Internal_All.csv")
                
                if not os.path.exists(internal_all_csv):
                    raise HTTPException(400, "Internal:All data not found in crawl results.")
                
                # Read and process the CSV data
                df = pd.read_csv(internal_all_csv).fillna("").astype(str)
                
                if df.empty:
                    raise HTTPException(400, "No data found in crawl results.")
                
                # Convert DataFrame to the format expected by KPI functions
                crawl_data = self._convert_df_to_kpi_format(df)
                
                # Calculate all KPIs
                dashboard_data = {
                    "indexability": indexability_kpis_and_table(crawl_data),
                    "status_code": status_code_kpis_and_table(crawl_data),
                    "page_title": page_title_kpis_and_table(crawl_data),
                    "meta_description": meta_description_kpis_and_tables(crawl_data),
                    "h_tags": h_tags_kpis_and_table(crawl_data)
                }
                
                # Save to database
                db_record = self._save_to_database(
                    uuid=batch_uuid,
                    user_id=user_id,
                    crawl_url=domain,
                    crawl_data=dashboard_data,
                    row_count=len(df),
                    is_seleted ="True"
                )
                
                return {
                    "success": True,
                    "message": f"Successfully crawled {domain} and saved to database",
                    "uuid": batch_uuid,
                    "rows_processed": len(df),
                    "database_id": db_record.id,
                    "dashboard_data": dashboard_data
                }
                
            except subprocess.CalledProcessError as e:
                raise HTTPException(500, f"Screaming Frog crawl failed: {e}")
            except Exception as e:
                raise HTTPException(500, f"Error during crawling and data processing: {e}")
    
    def _run_screaming_frog_crawl(self, domain: str, output_dir: str, tabs_arg: str):
        """Run a single Screaming Frog crawl exporting all specified tabs"""
        sf_path = os.environ.get("SF_PATH")
        if not sf_path or not os.path.exists(sf_path):
            raise HTTPException(500, "Screaming Frog SEO Spider not found. Please install it and set SF_PATH.")
        
        print(f"Starting Screaming Frog crawl for: {domain}")
        
        subprocess.run([
            sf_path,
            "--crawl", domain,
            "--headless",
            "--export-tabs", tabs_arg,
            "--output-folder", output_dir,
            "--overwrite"
        ], check=True, timeout=600)
    
    def _convert_df_to_kpi_format(self, df: pd.DataFrame) -> Dict:
        """Convert DataFrame to the format expected by KPI calculation functions"""
        # Convert DataFrame to list of dictionaries (rows)
        rows_data = df.to_dict('records')
        
        # Create headers list
        headers = df.columns.tolist()
        
        # Create the format expected by your KPI functions
        return {
            "values": [headers] + [list(row.values()) for row in rows_data]
        }
    
    def _save_to_database(
        self,
        uuid: str,
        user_id: int,
        crawl_url: str,
        crawl_data: Dict,
        row_count: int,
        is_seleted: str = "True"
    ) -> 'Sf_crawl_data':
        """Save crawl data to database"""
        
        # Create database record
        db_record = Sf_crawl_data(
            uuid=uuid,
            user_id=user_id,
            datatime=datetime.utcnow(),
            crawl_count=1,
            max_crawl=4,
            crawl_json_data=crawl_data,
            crawl_url=crawl_url,
            is_seleted="True"
        )
        
        # Add to database
        self.db.add(db_record)
        self.db.commit()
        self.db.refresh(db_record)
        
        return db_record
    
    def get_crawl_data_by_uuid(self, uuid: str, user_id: int) -> Dict:
        """Retrieve crawl data from database by UUID"""
        
        record = (
            self.db.query(Sf_crawl_data)
            .filter_by(uuid=uuid, user_id=user_id)
            .first()
        )
        
        if not record:
            raise HTTPException(404, f"No crawl data found for UUID {uuid}")
        
        return record.crawl_json_data