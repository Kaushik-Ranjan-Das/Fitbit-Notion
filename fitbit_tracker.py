# fitbit_tracker.py
import requests
from datetime import datetime
import os
import json

class FitbitNotionTracker:
    def __init__(self):
        print("\n=== Initializing FitbitNotionTracker ===")
        try:
            # Get credentials directly from environment variables
            self.fitbit_client_id = os.environ['FITBIT_CLIENT_ID']
            self.fitbit_client_secret = os.environ['FITBIT_CLIENT_SECRET']
            self.fitbit_access_token = os.environ['FITBIT_ACCESS_TOKEN']
            self.notion_token = os.environ['NOTION_TOKEN']
            self.notion_database_id = os.environ['NOTION_DATABASE_ID']
            
            # Validate credentials aren't empty
            for cred, value in {
                'FITBIT_CLIENT_ID': self.fitbit_client_id,
                'FITBIT_CLIENT_SECRET': self.fitbit_client_secret,
                'FITBIT_ACCESS_TOKEN': self.fitbit_access_token,
                'NOTION_TOKEN': self.notion_token,
                'NOTION_DATABASE_ID': self.notion_database_id
            }.items():
                if not value:
                    raise ValueError(f"{cred} is empty")
            
            print("✓ All credentials loaded successfully")
            
            # API endpoints
            self.fitbit_base_url = "https://api.fitbit.com/1/user/-/"
            self.notion_base_url = "https://api.notion.com/v1/"
            
        except KeyError as e:
            print(f"❌ Missing environment variable: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Error during initialization: {str(e)}")
            raise
    
    def get_daily_activity_minutes(self, date=None):
        """Fetch activity minutes from Fitbit"""
        print("\n=== Fetching Fitbit Activity Data ===")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        print(f"Fetching data for date: {date}")
            
        endpoint = f"activities/date/{date}.json"
        url = self.fitbit_base_url + endpoint
        print(f"Making request to: {url}")
        
        headers = {
            "Authorization": f"Bearer {self.fitbit_access_token}",
            "Accept": "application/json"
        }
        
        try:
            print("Sending request to Fitbit API...")
            response = requests.get(url, headers=headers)
            print(f"Response status code: {response.status_code}")
            
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

    def check_existing_entry(self, date):
        """Check if an entry already exists for the given date"""
        print(f"\n=== Checking Notion for existing entry on {date} ===")
        url = f"{self.notion_base_url}databases/{self.notion_database_id}/query"
        
        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        data = {
            "filter": {
                "property": "Date",
                "date": {
                    "equals": date
                }
            }
        }
        
        try:
            print("Querying Notion database...")
            response = requests.post(url, headers=headers, json=data)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Error response from Notion API: {response.text}")
            response.raise_for_status()
            
            results = response.json()['results']
            exists = len(results) > 0
            print(f"{'Found' if exists else 'No'} existing entry for {date}")
            return exists
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error checking Notion database: {str(e)}")
            print(f"Request details: URL={url}, Data={json.dumps(data)}")
            return None

    def post_to_notion(self, activity_data):
        """Post activity data to Notion database"""
        print("\n=== Posting to Notion Database ===")
        url = f"{self.notion_base_url}pages"
        
        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        properties = {
            "Date": {
                "type": "date",
                "date": {"start": activity_data['date']}
            },
            "Sedentary Minutes": {
                "type": "number",
                "number": activity_data['sedentary_minutes']
            },
            "Lightly Active Minutes": {
                "type": "number",
                "number": activity_data['lightly_active_minutes']
            },
            "Fairly Active Minutes": {
                "type": "number",
                "number": activity_data['fairly_active_minutes']
            },
            "Very Active Minutes": {
                "type": "number",
                "number": activity_data['very_active_minutes']
            },
            "Total Active Minutes": {
                "type": "number",
                "number": activity_data['total_active_minutes']
            }
        }
        
        data = {
            "parent": {"database_id": self.notion_database_id},
            "properties": properties
        }
        
        try:
            print("Sending data to Notion...")
            print("\nProperties being sent:")
            for key, value in properties.items():
                print(f"  {key}: {value}")
                
            response = requests.post(url, headers=headers, json=data)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Error response from Notion API: {response.text}")
            response.raise_for_status()
            
            print(f"✓ Successfully posted data to Notion for {activity_data['date']}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error posting to Notion: {str(e)}")
            print(f"Request details: URL={url}")
            print(f"Data being sent: {json.dumps(data, indent=2)}")
            return None

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
