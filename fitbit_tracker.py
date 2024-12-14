import requests
from datetime import datetime, timedelta
import os
import json
import base64
import time

class FitbitNotionTracker:
    def __init__(self):
        print("\n=== Initializing FitbitNotionTracker ===")
        try:
            # Get credentials from environment variables
            self.fitbit_client_id = os.environ['FITBIT_CLIENT_ID']
            self.fitbit_client_secret = os.environ['FITBIT_CLIENT_SECRET']
            self.fitbit_refresh_token = os.environ['FITBIT_REFRESH_TOKEN']
            self.notion_token = os.environ['NOTION_TOKEN']
            self.notion_database_id = os.environ['NOTION_DATABASE_ID']
            

            
            # Get initial access token using refresh token
            self.fitbit_access_token = self.refresh_fitbit_token()
            
            # API endpoints
            self.fitbit_base_url = "https://api.fitbit.com/1/user/-/"
            self.notion_base_url = "https://api.notion.com/v1/"
                        # Validate required credentials
            self._validate_credentials()
            print("✓ Initialization complete")
            
        except KeyError as e:
            print(f"❌ Missing environment variable: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Error during initialization: {str(e)}")
            raise

    def _validate_credentials(self):
        """Validate that all required credentials are present and well-formed"""
        if not self.fitbit_client_id or len(self.fitbit_client_id.strip()) == 0:
            raise ValueError("Invalid FITBIT_CLIENT_ID")
        if not self.fitbit_client_secret or len(self.fitbit_client_secret.strip()) == 0:
            raise ValueError("Invalid FITBIT_CLIENT_SECRET")
        if not self.fitbit_refresh_token or len(self.fitbit_refresh_token.strip()) == 0:
            raise ValueError("Invalid FITBIT_REFRESH_TOKEN")
        
        # Basic format check for refresh token
        if not self._is_valid_token_format(self.fitbit_refresh_token):
            raise ValueError("Refresh token appears to be malformed")

    def _is_valid_token_format(self, token):
        """Basic validation of token format"""
        # Tokens should be non-empty and contain only valid characters
        if not token or len(token.strip()) == 0:
            return False
        
        # Tokens are typically base64 encoded strings
        try:
            base64.b64decode(token.replace('-', '+').replace('_', '/') + '=' * (-len(token) % 4))
            return True
        except Exception:
            return False

    def refresh_fitbit_token(self, retry_count=3, retry_delay=5):
        """
        Refresh Fitbit access token using refresh token with retry mechanism
        """
        print("\n=== Refreshing Fitbit Token ===")
        
        url = "https://api.fitbit.com/oauth2/token"
        
        # Create Basic auth header
        auth_header = base64.b64encode(
            f"{self.fitbit_client_id}:{self.fitbit_client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.fitbit_refresh_token
        }
        
        last_error = None
        for attempt in range(retry_count):
            try:
                print(f"Requesting new access token (Attempt {attempt + 1}/{retry_count})...")
                response = requests.post(url, headers=headers, data=data)
                print(f"Response status code: {response.status_code}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    print("✓ Successfully refreshed token")
                    
                    # Update refresh token if a new one is provided
                    if 'refresh_token' in token_data:
                        self.fitbit_refresh_token = token_data['refresh_token']
                        os.environ['FITBIT_REFRESH_TOKEN'] = token_data['refresh_token']
                        print("ℹ️ New refresh token received and saved")
                    
                    return token_data['access_token']
                
                # Handle specific error cases
                error_data = response.json()
                if 'errors' in error_data:
                    error_type = error_data['errors'][0].get('errorType', '')
                    if error_type == 'invalid_grant':
                        print("❌ Refresh token is invalid. Please generate a new refresh token.")
                        raise ValueError("Invalid refresh token - needs to be regenerated")
                    elif error_type == 'invalid_client':
                        print("❌ Client credentials are invalid. Please check client ID and secret.")
                        raise ValueError("Invalid client credentials")
                
                print(f"❌ Error response: {response.text}")
                last_error = response
                
                if attempt < retry_count - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Network error during token refresh: {str(e)}")
                last_error = e
                if attempt < retry_count - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
        
        if isinstance(last_error, requests.Response):
            last_error.raise_for_status()
        raise last_error or Exception("Failed to refresh token after all retries")

    def _make_fitbit_request(self, endpoint, method='GET'):
        """
        Generic method to make Fitbit API requests with token refresh capability
        """
        url = self.fitbit_base_url + endpoint
        headers = {
            "Authorization": f"Bearer {self.fitbit_access_token}",
            "Accept": "application/json"
        }

        try:
            print(f"Sending {method} request to Fitbit API: {endpoint}")
            
            if method == 'GET':
                response = requests.get(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # If token expired, refresh and retry
            if response.status_code == 401:
                print("Token expired, refreshing...")
                self.fitbit_access_token = self.refresh_fitbit_token()
                headers["Authorization"] = f"Bearer {self.fitbit_access_token}"
                print("Retrying request with new token...")
                
                if method == 'GET':
                    response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print(f"❌ Error response from Fitbit API: {response.text}")
                response.raise_for_status()

            print("Successfully received data from Fitbit")
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error in Fitbit API request: {str(e)}")
            return None

    def get_comprehensive_health_data(self, date):
        """Retrieve comprehensive health data for a specific date"""
        print(f"\n=== Collecting Comprehensive Health Data for {date} ===")
        
        health_data = {
            'date': date,
            'activity': self.get_daily_activity_minutes(date),
            'sleep': self.get_sleep_data(date),
            'weight': self.get_weight_data(date),
            'heart_rate': self.get_heart_rate_data(date)
        }
        
        return health_data

    def get_daily_activity_minutes(self, date):
        """Fetch activity minutes from Fitbit"""
        print(f"\n=== Fetching Fitbit Activity Data for {date} ===")

        endpoint = f"activities/date/{date}.json"
        data = self._make_fitbit_request(endpoint)
        
        if data:
            activity_data = {
                'date': date,
                'sedentary_minutes': data['summary']['sedentaryMinutes'],
                'lightly_active_minutes': data['summary']['lightlyActiveMinutes'],
                'fairly_active_minutes': data['summary']['fairlyActiveMinutes'],
                'very_active_minutes': data['summary']['veryActiveMinutes'],
                'steps': data['summary']['steps'],
                'calories': data['summary'].get('caloriesOut', 0)
            }
            return activity_data
        return None

    def get_sleep_data(self, date):
        """Fetch sleep data from Fitbit"""
        print(f"\n=== Fetching Fitbit Sleep Data for {date} ===")
        
        endpoint = f"sleep/date/{date}.json"
        data = self._make_fitbit_request(endpoint)
        
        if data and data.get('summary'):
            sleep_data = {
                'date': date,
                'total_minutes_asleep': data['summary'].get('totalMinutesAsleep', 0),
                'total_sleep_records': data['summary'].get('totalSleepRecords', 0),
                'total_time_in_bed': data['summary'].get('totalTimeInBed', 0)
            }
            return sleep_data
        return None

    def get_weight_data(self, date):
        """Fetch weight data from Fitbit"""
        print(f"\n=== Fetching Fitbit Weight Data for {date} ===")
        
        endpoint = f"body/log/weight/date/{date}.json"
        data = self._make_fitbit_request(endpoint)
        
        if data and data.get('weight'):
            weight_entry = data['weight'][0] if data['weight'] else None
            
            if weight_entry:
                weight_data = {
                    'date': date,
                    'weight': weight_entry.get('weight', 0),
                    'bmi': weight_entry.get('bmi', 0),
                    'log_id': weight_entry.get('logId', '')
                }
                return weight_data
        return None

    def check_existing_entries(self, dates):
        """Check if entries for specific dates already exist in Notion"""
        print("\n=== Checking for Existing Notion Entries ===")
        
        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        filter_body = {
            "filter": {
                "or": [
                    {"property": "Date", "date": {"equals": date}} for date in dates
                ]
            }
        }
        
        url = f"{self.notion_base_url}databases/{self.notion_database_id}/query"
        
        try:
            response = requests.post(url, headers=headers, json=filter_body)
            response.raise_for_status()
            
            existing_entries = response.json()['results']
            existing_dates = [
                entry['properties']['Date']['date']['start'] 
                for entry in existing_entries 
                if entry['properties']['Date']['date']
            ]
            
            new_dates = [date for date in dates if date not in existing_dates]
            
            print(f"Existing entries found for: {existing_dates}")
            print(f"New dates to process: {new_dates}")
            
            return new_dates
        
        except Exception as e:
            print(f"❌ Error checking existing Notion entries: {str(e)}")
            return dates

    def post_to_notion(self, health_data):
        """Post health data to Notion database"""
        print("\n=== Posting Data to Notion ===")
        
        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        properties = {
            "Date": {
                "date": {"start": health_data['date']}
            }
        }
        
        for category, data in health_data.items():
            if category != 'date' and data:
                for key, value in data.items():
                    if key != 'date':
                        properties[key.replace('_', ' ').title()] = {
                            "number": value
                        }
        
        body = {
            "parent": {"database_id": self.notion_database_id},
            "properties": properties
        }
        
        url = f"{self.notion_base_url}pages"
        
        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            print(f"✓ Successfully posted data for {health_data['date']} to Notion")
        except Exception as e:
            print(f"❌ Error posting to Notion: {str(e)}")
            print(f"Request body: {json.dumps(body, indent=2)}")
            raise

def main():
    print("\n=== Starting Comprehensive Fitbit Health Data Collection ===")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        tracker = FitbitNotionTracker()
        
        # Generate dates for last 7 days
        today = datetime.now()
        date_range = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d") 
            for i in range(7)
        ]

        # Check which dates don't have existing entries
        dates_to_process = tracker.check_existing_entries(date_range)

        # Process and post data for new dates
        for date in dates_to_process:
            print(f"\nProcessing comprehensive data for date: {date}")
            
            # Collect comprehensive health data
            comprehensive_data = tracker.get_comprehensive_health_data(date)
            
            # Post to Notion
            tracker.post_to_notion(comprehensive_data)

            # Print out the collected data
            print("\n=== Comprehensive Health Data Summary ===")
            for category, data in comprehensive_data.items():
                if category != 'date':
                    print(f"\n{category.replace('_', ' ').title()}:")
                    if data:
                        for key, value in data.items():
                            print(f"  {key.replace('_', ' ').title()}: {value}")
                    else:
                        print("  No data available")
        
        if not dates_to_process:
            print("\n✓ No new dates to process. All entries up to date.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
