# fitbit_tracker.py
import requests
from datetime import datetime
import os

class FitbitNotionTracker:
    def __init__(self):
        # Get credentials directly from environment variables
        self.fitbit_client_id = os.environ['FITBIT_CLIENT_ID']
        self.fitbit_client_secret = os.environ['FITBIT_CLIENT_SECRET']
        self.fitbit_access_token = os.environ['FITBIT_ACCESS_TOKEN']
        self.notion_token = os.environ['NOTION_TOKEN']
        self.notion_database_id = os.environ['NOTION_DATABASE_ID']
        
        # API endpoints
        self.fitbit_base_url = "https://api.fitbit.com/1/user/-/"
        self.notion_base_url = "https://api.notion.com/v1/"
    
    def get_daily_activity_minutes(self, date=None):
        """Fetch activity minutes from Fitbit"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        endpoint = f"activities/date/{date}.json"
        url = self.fitbit_base_url + endpoint
        
        headers = {
            "Authorization": f"Bearer {self.fitbit_access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            return {
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
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Fitbit data: {str(e)}")
            return None

    def check_existing_entry(self, date):
        """Check if an entry already exists for the given date"""
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
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return len(response.json()['results']) > 0
            
        except requests.exceptions.RequestException as e:
            print(f"Error checking Notion database: {str(e)}")
            return None

    def post_to_notion(self, activity_data):
        """Post activity data to Notion database"""
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
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print(f"Successfully posted data to Notion for {activity_data['date']}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error posting to Notion: {str(e)}")
            return None

def main():
    try:
        tracker = FitbitNotionTracker()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if tracker.check_existing_entry(today):
            print(f"Entry for {today} already exists in Notion")
            return
        
        activity_data = tracker.get_daily_activity_minutes()
        
        if activity_data:
            tracker.post_to_notion(activity_data)
            print("\nToday's Activity Summary:")
            for key, value in activity_data.items():
                if key != 'date':
                    print(f"{key.replace('_', ' ').title()}: {value}")
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
