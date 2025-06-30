# sheets_service.py
import os
import subprocess
import pandas as pd
import tempfile
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta

from auth.models import Integration, ProviderEnum  

class GoogleSheetsService:
    def __init__(self, integration: Integration):
        self.integration = integration
        self.credentials = self._create_credentials()
        self.service = build('sheets', 'v4', credentials=self.credentials)
    
    def _create_credentials(self):
        """Create Google credentials from integration data"""
        return Credentials(
            token=self.integration.access_token,
            refresh_token=self.integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    
    def crawl_and_create_sheet(self, domain: str) -> dict:
        """
        Crawl domain with Screaming Frog and create Google Sheet
        """
        # Create temporary directory for this operation
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = os.path.join(temp_dir, "internal_all.csv")
            
            try:
                # 1. Run Screaming Frog crawl
                self._run_screaming_frog_crawl(domain, temp_dir)
                
                # 2. Check if CSV was created
                if not os.path.exists(csv_path):
                    raise HTTPException(500, "Screaming Frog crawl failed - CSV not found")
                
                # 3. Process CSV data
                df = pd.read_csv(csv_path)
                df = df.fillna("").astype(str)
                
                if df.empty:
                    raise HTTPException(400, "No data found in crawl")
                
                # 4. Create Google Sheet
                spreadsheet_result = self._create_google_sheet(domain, df)
                
                return spreadsheet_result
                
            except subprocess.CalledProcessError as e:
                raise HTTPException(500, f"Screaming Frog crawl failed: {str(e)}")
            except Exception as e:
                raise HTTPException(500, f"Error creating spreadsheet: {str(e)}")
    
    def _run_screaming_frog_crawl(self, domain: str, output_dir: str):
        """Run Screaming Frog crawl"""
        screaming_frog_path = r"C:\Program Files (x86)\Screaming Frog SEO Spider\screamingfrogseospider.exe"
        
        # Check if Screaming Frog exists
        if not os.path.exists(screaming_frog_path):
            raise HTTPException(500, "Screaming Frog SEO Spider not found. Please install it.")
        
        # Run the crawl
        subprocess.run([
            screaming_frog_path,
            "--crawl", domain,
            "--headless",
            "--export-tabs", "Internal:All",
            "--output-folder", output_dir,
            "--overwrite"
        ], check=True, timeout=300)  # 5 minute timeout
    
    def _create_google_sheet(self, domain: str, df: pd.DataFrame) -> dict:
        """Create Google Sheet with crawl data"""
        # Create spreadsheet
        sheet_metadata = {
            "properties": {
                "title": f"SEO Crawl - {domain} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
        }
        
        spreadsheet = self.service.spreadsheets().create(body=sheet_metadata).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']
        
        # Prepare data for Google Sheets
        values = [df.columns.tolist()] + df.values.tolist()
        
        # Write data to sheet
        body = {"values": values}
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A1",
            valueInputOption="RAW",
            body=body
        ).execute()
        
        # Format the header row
        # self._format_header_row(spreadsheet_id)
        
        return {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
            "rows_count": len(df),
            "columns_count": len(df.columns)
        }
    
    def _format_header_row(self, spreadsheet_id: str):
        """Format the header row (make it bold)"""
        try:
            requests = [{
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True},
                            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
                        }
                    },
                    "fields": "userEnteredFormat(textFormat,backgroundColor)"
                }
            }]
            
            body = {"requests": requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, 
                body=body
            ).execute()
        except Exception as e:
            print(f"Warning: Could not format header row: {e}")