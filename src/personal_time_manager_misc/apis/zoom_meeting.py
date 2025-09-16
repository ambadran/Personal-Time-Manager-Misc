'''

'''
import os
import requests
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
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
        # Reschedule past events ---
        try:
            start_time_dt = isoparse(start_time_iso)
            # Create a 'now' object that is timezone-aware in the same timezone as the event
            now_aware = datetime.now(start_time_dt.tzinfo)

            if start_time_dt < now_aware:
                original_time = start_time_dt.strftime('%Y-%m-%d %H:%M')
                start_time_dt += timedelta(days=7)
                start_time_iso = start_time_dt.isoformat()
                logger.warning(
                    f"Start time for '{topic}' ({original_time}) was in the past. "
                    f"Rescheduling to the same time next week: {start_time_iso}"
                )
        except Exception as e:
            logger.error(f"Could not parse or adjust start time '{start_time_iso}'. Error: {e}")
            return None

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
            start_dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
            
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

    def list_meetings(self, meeting_type: str = 'upcoming') -> list[dict] | None:
        """
        Lists all meetings for the user, handling pagination.

        Args:
            meeting_type (str): The type of meetings to list ('upcoming', 'live', etc.).
        
        Returns:
            A list of meeting dictionaries, or None if an error occurs.
        """
        token = self._get_access_token()
        if not token:
            logger.error("Cannot list meetings: failed to get access token.")
            return None

        headers = {"Authorization": f"Bearer {token}"}
        all_meetings = []
        next_page_token = ''
        try:
            while True:
                params = {'page_size': 300, 'type': meeting_type}
                if next_page_token:
                    params['next_page_token'] = next_page_token
                
                url = f"{self.base_url}/users/me/meetings"
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                all_meetings.extend(data.get('meetings', []))
                next_page_token = data.get('next_page_token')
                if not next_page_token:
                    break
            
            logger.info(f"Found a total of {len(all_meetings)} {meeting_type} meetings on the Zoom account.")
            return all_meetings
        except HTTPError as http_err:
            logger.critical(f"HTTP error listing Zoom meetings: {http_err.response.text}")
            return None

    def list_unique_meetings(self, topic_prefix: str = "Tuition ") -> dict[str, str] | None:
        """
        Finds unique recurring meeting series based on a topic prefix.

        Args:
            topic_prefix (str): The prefix to identify meetings managed by this app.
        
        Returns:
            A dictionary mapping each unique topic to one of its meeting IDs,
            or None if an error occurs.
        """
        all_occurrences = self.list_meetings(meeting_type='upcoming')
        if all_occurrences is None:
            return None # An error occurred during fetching

        unique_meeting_series = {}
        for meeting in all_occurrences:
            topic = meeting.get('topic')
            if topic and topic.startswith(topic_prefix):
                if topic not in unique_meeting_series:
                    unique_meeting_series[topic] = meeting['id']
        
        logger.info(f"Found {len(unique_meeting_series)} unique meeting series with prefix '{topic_prefix}'.")
        return unique_meeting_series

    def delete_all_automated_tuition_meetings(self):
        """
        Uses the list_meetings method to find and delete all automated tuition meetings.
        """
        logger.info("Starting cleanup of all automated tuition meetings from Zoom...")
        
        # 1. Use the new method to get unique meeting series
        unique_series = self.list_unique_meetings(topic_prefix="Tuition ")

        if unique_series is None:
            logger.critical("Could not retrieve unique meetings for cleanup. Aborting.")
            return

        if not unique_series:
            logger.info("No automated tuition meetings found to delete.")
            return

        # 2. Loop through the unique series and delete each one
        logger.warning(f"Found {len(unique_series)} unique meeting series that will be deleted.")
        deleted_count = 0
        for topic, meeting_id in unique_series.items():
            logger.info(f"Deleting entire series for topic: '{topic}'")
            if self.delete_meeting(meeting_id):
                deleted_count += 1
            
        logger.info(f"Cleanup complete. Successfully deleted {deleted_count} of {len(unique_series)} targeted meeting series.")

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    zoom_manager = ZoomMeetingManager()
    
    meeting_topic = "Test"
    start_time = datetime.now(timezone.utc) + timedelta(days=2)
    start_time_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(start_time_iso)

    print(zoom_manager.create_meeting(
        topic=meeting_topic,
        start_time_iso=start_time_iso,
        duration_minutes=60,
        timezone="Africa/Cairo"
    ))
