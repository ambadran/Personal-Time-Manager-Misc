'''

'''
import os
import requests
import datetime as dt
from dotenv import load_dotenv

class ZoomMeetingManager:
    """
    Manages creating Zoom meetings using Server-to-Server OAuth.
    """
    def __init__(self, account_id=None, client_id=None, client_secret=None):
        """
        Initializes the manager with your Zoom S2S OAuth credentials.

        """
        load_dotenv()
        if not account_id:
            self.account_id = os.environ.get("ZOOM_ACCOUNT_ID")
        if not client_id:
            self.client_id = os.environ.get("ZOOM_CLIENT_ID")
        if not client_secret:
            self.client_secret = os.environ.get("ZOOM_CLIENT_SECRET")

        self.base_url = "https://api.zoom.us/v2"
        self._access_token = None # To cache the token

    def _get_access_token(self):
        """
        Gets an access token from the Zoom OAuth endpoint.
        """
        url = "https://zoom.us/oauth/token"
        params = {
            "grant_type": "account_credentials",
            "account_id": self.account_id,
        }
        
        try:
            response = requests.post(url, auth=(self.client_id, self.client_secret), params=params)
            response.raise_for_status() # Check for HTTP errors
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            print("Successfully obtained new zoom access token.")
            return self._access_token
            
        except requests.exceptions.HTTPError as http_err:
            raise ValueError(f"HTTP error occurred while getting token: {http_err}\nResponse content: {response.content.decode()}")

        except Exception as err:
            print(f"An other error occurred: {err}")
            
        return None

    def create_meeting(self, topic, start_time_iso, duration_minutes, timezone="Africa/Cairo", recurrence_end_date_iso=None):
        """
        Creates a new Zoom meeting.
        """
        token = self._get_access_token()
        if not token:
            print("Failed to create meeting because access token could not be obtained.")
            return None
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/users/me/meetings"

        payload = {
            "topic": topic,
            "start_time": start_time_iso,
            "duration": duration_minutes,
            "timezone": timezone,
            "settings": {
                "join_before_host": True,
                "mute_upon_entry": True,
            },
        }

        if recurrence_end_date_iso:
            print("creating recurring meeting")
            # --- Logic for a RECURRING meeting ---
            payload["type"] = 8  # '8' for a recurring meeting
            payload["start_time"] = start_time_iso
            
            # Parse start time to figure out the day of the week
            start_dt = dt.datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
            
            # Zoom's weekly_days format: 1=Sunday, 2=Monday, ..., 7=Saturday
            # Python's isoweekday() format: 1=Monday, ..., 6=Saturday, 7=Sunday
            # We convert Python's day to Zoom's day
            zoom_weekday = (start_dt.isoweekday() % 7) + 1

            payload["recurrence"] = {
                "type": 2,  # '2' for weekly
                "repeat_interval": 1,
                "weekly_days": str(zoom_weekday),
                "end_date_time": recurrence_end_date_iso
            }

        else:
            # --- Logic for a NORMAL (non-recurring) meeting ---
            payload["type"] = 2  # '2' for a standard scheduled meeting
            payload["start_time"] = start_time_iso

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            meeting_data = response.json()
            print("\nZoom meeting created successfully!")
            print(f"   Topic: {meeting_data['topic']}")
            # print(f"   Join URL: {meeting_data['join_url']}")


            # Return both the ID and the join URL
            return meeting_data.get('id'), meeting_data.get('join_url')

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred while creating meeting: {http_err}")
            print(f"Response content: {response.content.decode()}")
        except Exception as err:
            print(f"An other error occurred: {err}")
        
        return None

    def delete_meeting(self, meeting_id):
        """
        Deletes a specific Zoom meeting using its ID.
        """
        token = self._get_access_token()
        if not token:
            print(f"Failed to delete meeting {meeting_id}: access token could not be obtained.")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/meetings/{meeting_id}"

        try:
            response = requests.delete(url, headers=headers)
            if response.status_code == 204:
                print(f"\nMeeting with ID {meeting_id} was successfully deleted.")
                return True
            else:
                response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred while deleting meeting: {http_err}")
        
        return False

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    zoom_manager = ZoomMeetingManager()
    
    meeting_topic = "Test"
    start_time = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=2)
    start_time_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(start_time_iso)

    print(zoom_manager.create_meeting(
        topic=meeting_topic,
        start_time_iso=start_time_iso,
        duration_minutes=60,
        timezone="Africa/Cairo"
    ))
