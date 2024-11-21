import requests
from datetime import datetime
import os
import json
import base64

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
            
            print("✓ Initialization complete")
            
        except KeyError as e:
            print(f"❌ Missing environment variable: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Error during initialization: {str(e)}")
            raise

    def refresh_fitbit_token(self):
        """Refresh Fitbit access token using refresh token"""
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
        
        try:
            print("Requesting new access token...")
            response = requests.post(url, headers=headers, data=data)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Error refreshing token: {response.text}")
                response.raise_for_status()
            
            token_data = response.json()
            print("✓ Successfully refreshed token")
            
            # Update refresh token if a new one is provided
            if 'refresh_token' in token_data:
                self.fitbit_refresh_token = token_data['refresh_token']
                print("ℹ️ New refresh token received")
            
            return token_data['access_token']
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error refreshing token: {str(e)}")
            raise

    def get_daily_activity_minutes(self, date=None):
        """Fetch activity minutes from Fitbit"""
        print("\n=== Fetching Fitbit Activity Data ===")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        print(f"Fetching data for date: {date}")
            
        endpoint = f"activities/date/{date}.json"
        url = self.fitbit_base_url + endpoint
        
        headers = {
            "Authorization": f"Bearer {self.fitbit_access_token}",
            "Accept": "application/json"
        }
        
        try:
            print("Sending request to Fitbit API...")
            response = requests.get(url, headers=headers)
            print(f"Response status code: {response.status_code}")
            
            # If token expired, refresh and retry
            if response.status_code == 401:
                print("Token expired, refreshing...")
                self.fitbit_access_token = self.refresh_fitbit_token()
                headers["Authorization"] = f"Bearer {self.fitbit_access_token}"
                print("Retrying request with new token...")
                response = requests.get(url, headers=headers)
                print(f"New response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Error response from Fitbit API: {response.text}")
            response.raise_for_status()
            
            data = response.json()
            print("Successfully received data from Fitbit")
            
            activity_data = {
                'date': date,
                'sedentary_minutes': data['summary']['sedentaryMinutes'],
                'lightly_active_minutes': data['summary']['lightlyActiveMinutes'],
                'fairly_active_minutes': data['summary']['fairlyActiveMinutes'],
                'very_active_minutes': data['summary']['veryActiveMinutes'],
                'total_active_minutes': (
                    data['summary']['lightlyActiveMinutes'] +
                    data['summary']['fairlyActiveMinutes'] +
                    data['summary']['veryActiveMinutes']
                )
            }
            
            print("\nActivity data summary:")
            for key, value in activity_data.items():
                print(f"  {key}: {value}")
            
            return activity_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching Fitbit data: {str(e)}")
            print(f"Request details: URL={url}")
            return None

    # [Previous Notion methods remain the same...]

def main():
    print("\n=== Starting Fitbit to Notion Sync ===")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        tracker = FitbitNotionTracker()
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\nProcessing data for date: {today}")
        
        print("\nStep 1: Checking for existing entry")
        if tracker.check_existing_entry(today):
            print(f"⚠️ Entry for {today} already exists in Notion")
            return
        
        print("\nStep 2: Fetching Fitbit data")
        activity_data = tracker.get_daily_activity_minutes()
        
        if activity_data:
            print("\nStep 3: Posting to Notion")
            tracker.post_to_notion(activity_data)
            
            print("\n=== Final Activity Summary ===")
            for key, value in activity_data.items():
                if key != 'date':
                    print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            print("❌ No activity data received from Fitbit")
            
    except Exception as e:
        print(f"\n❌ Error in main execution: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
