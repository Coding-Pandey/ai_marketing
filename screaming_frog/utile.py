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

import os
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict

import pandas as pd
from fastapi import HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GoogleSheetsService:
    def __init__(self, integration: Integration):
        self.integration = integration
        self.credentials = self._create_credentials()
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.sheets_api = self.service.spreadsheets()

    def _create_credentials(self) -> Credentials:
        """Create Google credentials from integration data"""
        return Credentials(
            token=self.integration.access_token,
            refresh_token=self.integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

    def crawl_and_create_sheets(
        self,
        domain: str,
        export_tabs: List[str]
    ) -> List[Dict]:
        """
        Crawl domain once with Screaming Frog and export multiple tabs in a single run,
        then create a separate Google Sheet for each CSV export.

        :param domain: Domain to crawl
        :param export_tabs: List of Screaming Frog tab names (e.g. ['Internal:All','External','Images'])
        :return: List of results per sheet
        """
        if not export_tabs:
            raise HTTPException(400, "At least one export tab must be specified.")

        # Prepare comma-separated tabs for Screaming Frog
        tabs_arg = ",".join(export_tabs)
        print(tabs_arg)
        results: List[Dict] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Using temporary directory: {temp_dir}")
            try:
                # Single crawl for all tabs
                self._run_screaming_frog_crawl(domain, temp_dir, tabs_arg)

                # Process each CSV output
                for tab in export_tabs:
                    print(f"Processing tab: {tab}")
                    csv_name = tab.replace(':', '_') + '.csv'
                    csv_path = os.path.join(temp_dir, csv_name)

                    if not os.path.exists(csv_path):
                        # Skip missing exports
                        continue

                    df = pd.read_csv(csv_path).fillna("").astype(str)
                    if df.empty:
                        print("{tab} empty")
                        continue

                    sheet_info = self._create_google_sheet(domain, tab, df)
                    print(sheet_info)
                    results.append(sheet_info)
                    # change functiion 

                if not results:
                    raise HTTPException(400, "No data found in any specified crawl tabs.")

                return results

            except subprocess.CalledProcessError as e:
                raise HTTPException(500, f"Screaming Frog crawl failed: {e}")
            except Exception as e:
                raise HTTPException(500, f"Error during crawling and sheet creation: {e}")

    def _run_screaming_frog_crawl(self, domain: str, output_dir: str, tabs_arg: str):
        """Run a single Screaming Frog crawl exporting all specified tabs"""
        # sf_path = "C:\\Program Files (x86)\\Screaming Frog SEO Spider\\screamingfrogseospider.exe"
        sf_path = os.environ.get("SF_PATH")
        if not os.path.exists(sf_path):
            raise HTTPException(500, "Screaming Frog SEO Spider not found. Please install it.")
        
        print("hello")

        subprocess.run([
            # "xvfb-run", "-a",
            sf_path,
            "--crawl", domain,
            "--headless",
            "--export-tabs", tabs_arg,
            "--output-folder", output_dir,
            "--overwrite"
        ], check=True, timeout=600)

    def _create_google_sheet(
        self,
        domain: str,
        tab_name: str,
        df: pd.DataFrame
    ) -> Dict:
        """Create a Google Sheet containing the DataFrame"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        title = f"SEO Crawl - {domain} - {tab_name} - {timestamp}"
        spreadsheet = self.service.spreadsheets().create(
            body={"properties": {"title": title}}
        ).execute()
        sid = spreadsheet['spreadsheetId']

        values = [df.columns.tolist()] + df.values.tolist()
        self.service.spreadsheets().values().update(
            spreadsheetId=sid,
            range="A1",
            valueInputOption="RAW",
            body={"values": values}
        ).execute()

        return {
            "tab": tab_name,
            "domain"
            "spreadsheet_id": sid,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{sid}/edit",
            "rows_count": len(df),
            "columns_count": len(df.columns)
        }

    def _format_header_row(self, spreadsheet_id: str):
        """Optional: make the first row bold"""
        try:
            requests = [{
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat"
                }
            }]
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()
        except Exception as e:
            print(f"Warning: Could not format header row: {e}")
            
            
    def list_tabs(self, spreadsheet_id: str) -> List[str]:
        """Return all sheet/tab names in a spreadsheet."""
        metadata = self.sheets_api.get(spreadsheetId=spreadsheet_id).execute()
        sheets = metadata.get("sheets", [])
        return [s["properties"]["title"] for s in sheets]

    def get_sheet_values(self, spreadsheet_id: str, sheet_name: str) -> List[List[str]]:
        """Fetch the raw cell values for a given sheet/tab."""
        resp = (
            self.sheets_api
            .values()
            .get(spreadsheetId=spreadsheet_id, range=sheet_name)
            .execute()
        )
        return resp.get("values", [])
