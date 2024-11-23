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
            
            # Validate required credentials
            self._validate_credentials()
            
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
            # Try to decode as base64 (this doesn't guarantee it's a valid token,
            # but helps catch obviously invalid ones)
            base64.b64decode(token.replace('-', '+').replace('_', '/') + '=' * (-len(token) % 4))
            return True
        except Exception:
            return False

    def refresh_fitbit_token(self, retry_count=3, retry_delay=5):
        """
        Refresh Fitbit access token using refresh token with retry mechanism
        
        :param retry_count: Number of times to retry on failure
        :param retry_delay: Delay in seconds between retries
        :return: New access token
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
                        # Save the new refresh token to environment variable
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
                
                # Wait before retrying
                if attempt < retry_count - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Network error during token refresh: {str(e)}")
                last_error = e
                if attempt < retry_count - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
        
        # If we've exhausted all retries, raise the last error
        if isinstance(last_error, requests.Response):
            last_error.raise_for_status()
        raise last_error or Exception("Failed to refresh token after all retries")
