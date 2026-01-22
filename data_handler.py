"""
Data handling and export functionality
"""
import json
import csv
import os
import re
import base64
from typing import List, Dict, Optional
from datetime import datetime
import pytz
import pandas as pd
from config import get_config

# Australian timezone
AUSTRALIA_TZ = pytz.timezone('Australia/Sydney')

# Google Sheets API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("Warning: Google Sheets API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


class DataHandler:
    """Handle data storage and export"""
    
    def __init__(self):
        self.config = get_config()
        self.output_dir = self.config["output"]["dir"]
        self.data_file = self.config["output"]["data_file"]
        self.csv_file = self.config["output"]["csv_file"]
        self._ensure_output_dir()
        
        # Google Sheets configuration
        self.sheets_config = self.config.get("google_sheets", {})
        self.sheet_id = self.sheets_config.get("sheet_id")
        self.sheet_range = self.sheets_config.get("range", "Sheet1!A:Z")
        self.credentials_file = self.sheets_config.get("credentials_file", "credentials.json")
        self.token_file = self.sheets_config.get("token_file", "token.json")
        self.service = None
        # Last Google Sheets write status (for debugging / API callback)
        self.last_sheets_error: Optional[str] = None
        self.last_sheets_url: Optional[str] = None
    
    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def _clear_output_files(self):
        """Clear old output files from output directory"""
        try:
            if os.path.exists(self.output_dir):
                # List of default output files to remove
                files_to_remove = [
                    self.data_file,
                    self.csv_file,
                ]
                
                # Also remove any timestamped Excel files
                for file in os.listdir(self.output_dir):
                    if file.startswith("gumtree_data_") and file.endswith(".xlsx"):
                        files_to_remove.append(os.path.join(self.output_dir, file))
                
                # Remove files if they exist
                for file_path in files_to_remove:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"Removed old file: {file_path}")
                        except Exception as e:
                            print(f"Warning: Could not remove {file_path}: {e}")
        except Exception as e:
            print(f"Warning: Error clearing output files: {e}")
    
    def save_json(self, data: List[Dict], filename: str = None) -> str:
        """
        Save data to JSON file
        
        Args:
            data: List of dictionaries to save
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        filename = filename or self.data_file
        
        # Add metadata with Australian timezone
        aus_time = datetime.now(AUSTRALIA_TZ)
        output_data = {
            "metadata": {
                "scraped_at": aus_time.isoformat(),
                "total_items": len(data),
            },
            "data": data,
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filename}")
        return filename
    
    def save_csv(self, data: List[Dict], filename: str = None) -> str:
        """
        Save data to CSV file
        
        Args:
            data: List of dictionaries to save
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        if not data:
            print("No data to save")
            return ""
        
        filename = filename or self.csv_file
        
        # Flatten nested dictionaries
        flattened_data = []
        for item in data:
            flattened_item = self._flatten_dict(item)
            flattened_data.append(flattened_item)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(flattened_data)
        df.to_csv(filename, index=False, encoding="utf-8")
        
        print(f"Data saved to {filename}")
        return filename
    
    def _flatten_dict(self, d: Dict, parent_key: str = "", sep: str = "_") -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert list to string representation
                items.append((new_key, json.dumps(v) if v else ""))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def load_json(self, filename: str = None) -> List[Dict]:
        """
        Load data from JSON file
        
        Args:
            filename: Optional custom filename
        
        Returns:
            List of dictionaries
        """
        filename = filename or self.data_file
        
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
            return []
        
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract data from metadata wrapper if present
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        
        return data if isinstance(data, list) else []
    
    def append_data(self, new_data: List[Dict], filename: str = None) -> str:
        """
        Append new data to existing JSON file
        
        Args:
            new_data: New data to append
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        filename = filename or self.data_file
        
        # Load existing data
        existing_data = self.load_json(filename)
        
        # Combine data (avoid duplicates based on URL)
        existing_urls = {item.get("url") for item in existing_data if item.get("url")}
        for item in new_data:
            if item.get("url") not in existing_urls:
                existing_data.append(item)
                existing_urls.add(item.get("url"))
        
        # Save combined data
        return self.save_json(existing_data, filename)
    
    def export_to_excel(self, data: List[Dict], filename: str = None) -> str:
        """
        Export data to Excel file
        
        Args:
            data: List of dictionaries to export
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        if not data:
            print("No data to export")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/gumtree_data_{timestamp}.xlsx"
        
        # Flatten nested dictionaries
        flattened_data = []
        for item in data:
            flattened_item = self._flatten_dict(item)
            flattened_data.append(flattened_item)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(flattened_data)
        df.to_excel(filename, index=False, engine="openpyxl")
        
        print(f"Data exported to {filename}")
        return filename
    
    def get_statistics(self, data: List[Dict]) -> Dict:
        """
        Get statistics about the scraped data
        
        Args:
            data: List of dictionaries
        
        Returns:
            Dictionary with statistics
        """
        if not data:
            return {"total_items": 0}
        
        stats = {
            "total_items": len(data),
            "items_with_price": sum(1 for item in data if item.get("price")),
            "items_with_location": sum(1 for item in data if item.get("location")),
            "items_with_images": sum(1 for item in data if item.get("images")),
        }
        
        # Price statistics
        prices = []
        for item in data:
            price = item.get("price", "")
            if price:
                # Extract numeric value
                price_match = re.search(r"[\d,]+", str(price).replace(",", ""))
                if price_match:
                    try:
                        prices.append(float(price_match.group()))
                    except ValueError:
                        pass
        
        if prices:
            stats["price_stats"] = {
                "min": min(prices),
                "max": max(prices),
                "average": sum(prices) / len(prices),
            }
        
        return stats
    
    def _get_google_sheets_service(self):
        """Get authenticated Google Sheets service"""
        if not GOOGLE_SHEETS_AVAILABLE:
            raise ImportError("Google Sheets API libraries not installed")
        
        if self.service:
            return self.service
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = None
        
        # Check for credentials in environment variables (Railway deployment)
        google_creds_env = os.environ.get("GOOGLE_CREDENTIALS")
        google_token_env = os.environ.get("GOOGLE_TOKEN")
        
        # Try to load token from environment variable first (Railway)
        if google_token_env:
            try:
                # Token from env var is JSON string
                token_data = json.loads(google_token_env)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                print("Loaded credentials from GOOGLE_TOKEN environment variable")
            except json.JSONDecodeError as e:
                print(f"Error: GOOGLE_TOKEN is not valid JSON: {e}")
                print("Make sure GOOGLE_TOKEN contains the full JSON from token.json")
                creds = None
            except Exception as e:
                print(f"Warning: Could not load credentials from GOOGLE_TOKEN: {e}")
                creds = None
        
        # Fallback: Load existing token from file (local development)
        if not creds and os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Try to refresh the token
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Warning: Could not refresh token: {e}")
                    creds = None
            
            # If still no valid credentials, we need to get new ones
            if not creds or not creds.valid:
                # On Railway, we can't do interactive auth
                # We must have GOOGLE_TOKEN set
                if google_token_env:
                    raise FileNotFoundError(
                        "Google token from GOOGLE_TOKEN environment variable is invalid or expired.\n"
                        "Please generate a new token.json file and update GOOGLE_TOKEN in Railway."
                    )
                elif google_creds_env:
                    raise FileNotFoundError(
                        "GOOGLE_CREDENTIALS is set but GOOGLE_TOKEN is missing or invalid.\n"
                        "On Railway, you need both GOOGLE_CREDENTIALS and GOOGLE_TOKEN environment variables.\n"
                        "Interactive authentication is not available on Railway."
                    )
                else:
                    # Fallback: Try to load from files (local development only)
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(
                            f"Google credentials file not found: {self.credentials_file}\n"
                            "Please download credentials.json from Google Cloud Console\n"
                            "Or set GOOGLE_CREDENTIALS and GOOGLE_TOKEN environment variables"
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run (only if not on Railway)
            if not google_token_env and os.path.exists(os.path.dirname(self.token_file) or '.'):
                try:
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"Warning: Could not save token file: {e}")
        
        self.service = build('sheets', 'v4', credentials=creds)
        return self.service
    
    def _read_existing_sheet_data(self) -> List[Dict]:
        """Read existing data from Google Sheets"""
        try:
            service = self._get_google_sheets_service()
            
            # Read existing data
            result = service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=self.sheet_range
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return []
            
            # First row is headers
            headers = values[0]
            existing_data = []
            
            # Convert rows to dictionaries
            for row in values[1:]:
                if row:  # Skip empty rows
                    item = {}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            item[header] = row[i]
                        else:
                            item[header] = ""
                    existing_data.append(item)
            
            return existing_data
            
        except HttpError as error:
            print(f"Error reading from Google Sheets: {error}")
            return []
    
    def save_to_google_sheets(self, data: List[Dict]) -> bool:
        """
        Save data to Google Sheets, appending only new records
        
        Args:
            data: List of dictionaries to save
            
        Returns:
            True if successful, False otherwise
        """
        # Reset last status
        self.last_sheets_error = None
        self.last_sheets_url = None

        if not GOOGLE_SHEETS_AVAILABLE:
            print("Error: Google Sheets API libraries not installed")
            self.last_sheets_error = "Google Sheets libraries not installed"
            return False
        
        if not self.sheet_id:
            print("Error: Google Sheets ID not configured")
            self.last_sheets_error = "Google Sheets ID not configured"
            return False
        
        if not data:
            print("No data to save to Google Sheets")
            self.last_sheets_error = "No data to save"
            return False
        
        try:
            service = self._get_google_sheets_service()

            # Determine sheet/tab name from configured range (default to Sheet1)
            # Examples:
            #   "Sheet1!A:Z" -> "Sheet1"
            #   "Jobs!A:Z"   -> "Jobs"
            sheet_name = "Sheet1"
            try:
                if isinstance(self.sheet_range, str) and "!" in self.sheet_range:
                    sheet_name = self.sheet_range.split("!", 1)[0] or "Sheet1"
            except Exception:
                sheet_name = "Sheet1"
            
            # Read existing data to check for duplicates
            existing_data = self._read_existing_sheet_data()
            
            # Create set of existing job_ids and URLs for duplicate detection
            existing_job_ids = {item.get("job_id") for item in existing_data if item.get("job_id")}
            existing_urls = {item.get("url") for item in existing_data if item.get("url")}
            
            # Filter out duplicates
            new_data = []
            for item in data:
                job_id = item.get("job_id")
                url = item.get("url")
                
                # Skip if job_id or URL already exists
                if job_id and job_id in existing_job_ids:
                    continue
                if url and url in existing_urls:
                    continue
                
                new_data.append(item)
                # Add to existing sets to avoid duplicates within new_data
                if job_id:
                    existing_job_ids.add(job_id)
                if url:
                    existing_urls.add(url)
            
            if not new_data:
                print("No new data to append to Google Sheets (all records already exist)")
                return True
            
            print(f"Appending {len(new_data)} new records to Google Sheets (skipped {len(data) - len(new_data)} duplicates)")
            
            # Define column order to match JSON format
            preferred_order = [
                "job_id",
                "title",
                "url",
                "location",
                "categoryName",
                "creationDate",
                "description",
                "phone",
                "phoneNumberExists",
                "phoneRevealUrl",
                "scraped_at",
                "lastEdited",
                "success"
            ]
            
            # Flatten data for Google Sheets
            flattened_data = []
            for item in new_data:
                flattened_item = self._flatten_dict(item)
                flattened_data.append(flattened_item)
            
            # Get all unique keys from all items
            all_keys = set()
            for item in flattened_data:
                all_keys.update(item.keys())
            
            # Use preferred order, then add any additional keys alphabetically
            headers = []
            for key in preferred_order:
                if key in all_keys:
                    headers.append(key)
            
            # Add any remaining keys that weren't in preferred order
            remaining_keys = sorted(all_keys - set(preferred_order))
            headers.extend(remaining_keys)
            
            # Check if sheet is empty (first run)
            result = service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!A1:Z1"
            ).execute()
            
            values = result.get('values', [])
            
            # Prepare data rows
            rows = []
            if not values:
                # First run - add headers
                rows.append(headers)
            
            # Add data rows
            for item in flattened_data:
                row = []
                for header in headers:
                    value = item.get(header, "")
                    # Convert None/null to empty string, keep other values as strings
                    if value is None:
                        row.append("")
                    else:
                        str_value = str(value)
                        # Fix phone numbers starting with + to prevent formula errors in Google Sheets
                        # Prefix with single quote to force text format
                        if header == "phone" and str_value and str_value.startswith("+"):
                            str_value = "'" + str_value
                        row.append(str_value)
                rows.append(row)
            
            # Determine range for append
            if not values:
                # First run - write headers and data
                range_name = f"{sheet_name}!A1"
            else:
                # Append mode - find next empty row
                result = service.spreadsheets().values().get(
                    spreadsheetId=self.sheet_id,
                    range=f"{sheet_name}!A:A"
                ).execute()
                existing_rows = result.get('values', [])
                next_row = len(existing_rows) + 1
                range_name = f"{sheet_name}!A{next_row}"
            
            # Write data to sheet
            body = {
                'values': rows
            }
            
            if not values:
                # First run - use update
                service.spreadsheets().values().update(
                    spreadsheetId=self.sheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            else:
                # Append mode
                service.spreadsheets().values().append(
                    spreadsheetId=self.sheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()
            
            print(f"Successfully appended {len(new_data)} records to Google Sheets")
            self.last_sheets_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/edit"
            print(f"Sheet URL: {self.last_sheets_url}")
            return True
            
        except HttpError as error:
            print(f"Error writing to Google Sheets: {error}")
            self.last_sheets_error = str(error)
            return False
        except Exception as e:
            print(f"Unexpected error saving to Google Sheets: {e}")
            self.last_sheets_error = str(e)
            import traceback
            traceback.print_exc()
            return False
