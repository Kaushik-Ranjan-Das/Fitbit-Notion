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
    
    # Rest of the code remains exactly the same as in the previous version
    # (Copy all the methods from the previous version)

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
