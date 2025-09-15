'''

'''
import os
import requests
import datetime as dt
from dotenv import load_dotenv
from ..common.logger import logger
from requests.exceptions import HTTPError

class ZoomMeetingManager:
    """
    Manages creating Zoom meetings using Server-to-Server OAuth.
    """
    def __init__(self, account_id=None, client_id=None, client_secret=None):
        """
        Initializes the manager with your Zoom S2S OAuth credentials.

        """
        load_dotenv()
        self.account_id = account_id or os.environ.get("ZOOM_ACCOUNT_ID")
        self.client_id = client_id or os.environ.get("ZOOM_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("ZOOM_CLIENT_SECRET")

        if not all([self.account_id, self.client_id, self.client_secret]):
            raise ValueError("Zoom credentials (ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET) are not fully configured.")

        self.base_url = "https://api.zoom.us/v2"
        self._access_token = None

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
            logger.info("Successfully obtained new zoom access token.")
            return self._access_token

        except HTTPError as http_err:
            logger.critical(f"HTTP error getting Zoom token: {http_err}\nResponse: {http_err.response.text}")
        except Exception as err:
            logger.critical(f"An unexpected error occurred while getting Zoom token: {err}")
            
        return None

    def create_meeting(self, topic, start_time_iso, duration_minutes, timezone="Africa/Cairo", recurrence_end_date_iso=None):
        """
        Creates a new Zoom meeting.
        """
        token = self._get_access_token()
        if not token:
            logger.error("Failed to create meeting: could not get access token.")
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
            logger.info(f"Creating recurring meeting for '{topic}'")
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

            logger.info(f"Zoom meeting created successfully: {meeting_data['topic']}")
            # Return both the ID and the join URL
            return meeting_data.get('id'), meeting_data.get('join_url')

        except HTTPError as http_err:
            logger.error(f"HTTP error creating meeting: {http_err}\nResponse: {response.text}")
        except Exception as err:
            logger.exception(f"An unexpected error occurred creating meeting: {err}")
        return None

    def delete_meeting(self, meeting_id):
        """
        Deletes a specific Zoom meeting using its ID.
        """
        token = self._get_access_token()
        if not token:
            logger.error(f"Failed to delete meeting {meeting_id}: could not get access token.")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/meetings/{meeting_id}"

        try:
            response = requests.delete(url, headers=headers)
            if response.status_code == 204:
                logger.info(f"Meeting with ID {meeting_id} was successfully deleted.")
                return True
            elif response.status_code == 404:
                logger.warning(f"Attempted to delete meeting {meeting_id}, but it was not found on Zoom.")
                return True # If it's not there, the goal is achieved.
            else:
                response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error deleting meeting {meeting_id}: {http_err}\nResponse: {response.text}")
        return False

    def delete_all_automated_tuition_meetings(self):
        """
        Fetches all meetings from Zoom and deletes any whose topic starts with 'Tuition '.
        This is intended for manual cleanup only.
        """
        logger.info("Starting cleanup of all automated tuition meetings from Zoom...")
        token = self._get_access_token()
        if not token:
            logger.critical("Cannot start cleanup: failed to get access token.")
            return

        headers = {"Authorization": f"Bearer {token}"}
        all_meetings = []
        next_page_token = ''

        try:
            while True:
                params = {'page_size': 300}
                if next_page_token:
                    params['next_page_token'] = next_page_token
                
                # FIX: This method requires the specific user_id.
                url = f"{self.base_url}/users/me/meetings"
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
               
                all_meetings.extend(data.get('meetings', []))
                next_page_token = data.get('next_page_token')
                if not next_page_token:
                    break
            
            logger.info(f"Found a total of {len(all_meetings)} meetings on the Zoom account.")

        except HTTPError as http_err:
            # This is the specific block to catch web errors
            logger.critical("An HTTP error occurred while trying to list Zoom meetings.")
            logger.critical(f"Request URL: {http_err.request.url}")
            logger.critical(f"Status Code: {http_err.response.status_code}")
            # This is the key: print the detailed error message from Zoom's server
            logger.critical(f"Response Body: {http_err.response.text}")
            return # Abort the function
            
        except Exception as e:
            # General catch-all for other unexpected errors (e.g., network issues)
            logger.critical(f"A non-HTTP error occurred while listing Zoom meetings. Aborting. Error: {e}")
            return
        
        meetings_to_delete = [m for m in all_meetings if m.get('topic', '').startswith("Tuition ")]
        if not meetings_to_delete:
            logger.info("No automated tuition meetings found to delete.")
            return

        logger.warning(f"Found {len(meetings_to_delete)} meetings that will be deleted.")
        deleted_count = 0
        for meeting in meetings_to_delete:
            if self.delete_meeting(meeting['id']):
                deleted_count += 1
            
        logger.info(f"Cleanup complete. Successfully deleted {deleted_count} of {len(meetings_to_delete)} targeted meetings.")


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
