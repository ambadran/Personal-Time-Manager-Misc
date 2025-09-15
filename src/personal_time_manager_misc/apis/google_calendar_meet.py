'''

'''
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from dateutil.parser import isoparse # Make sure to have python-dateutil installed
from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from ..common.logger import logger
from ..common.config import DEFAULT_TIMEZONE

class GoogleCalendarManager:
    """
    Manages all interactions with the Google Calendar API using a service account.
    """
    def __init__(self):
        load_dotenv()
        self.creds = None
        self.service = self._authenticate()
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        if not self.calendar_id:
            raise ValueError("GOOGLE_CALENDAR_ID is not set in the environment.")

    def _authenticate(self) -> Resource | None:
        """Authenticates using the service account JSON file."""
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        if not creds_path:
            raise ValueError("GOOGLE_CREDENTIALS_PATH is not set in the environment.")
        
        try:
            scopes = ['https://www.googleapis.com/auth/calendar']
            creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=scopes)
            logger.info("Successfully authenticated with Google Calendar API.")
            return build('calendar', 'v3', credentials=creds)

        except Exception as e:
            logger.error(f"Error occurred in authentication:\n{e}")
            return None

    def _build_event_body(self, 
            event_key: str, 
            summary: str, 
            start_time_iso: str, 
            end_time_iso: str, 
            timezone: str = DEFAULT_TIMEZONE,
            recurrence_end_date_iso: str | None = None):
        """Helper to construct the event dictionary for the API."""
        event_body = {
            'summary': summary,
            'start': {'dateTime': start_time_iso, 'timeZone': timezone},
            'end': {'dateTime': end_time_iso, 'timeZone': timezone},
            'extendedProperties': {
                'private': {'ptm_event_key': event_key}
            }
        }
        
        if recurrence_end_date_iso:
            try:
                # The RRULE UNTIL format must be YYYYMMDDTHHMMSSZ (no hyphens or colons)
                end_date_dt = isoparse(recurrence_end_date_iso)
                until_format = end_date_dt.strftime('%Y%m%dT%H%M%SZ')
                
                # Create a rule for a weekly recurring event
                event_body['recurrence'] = [f"RRULE:FREQ=WEEKLY;UNTIL={until_format}"]
                logger.debug(f"Added recurrence rule to '{summary}'")
            except Exception as e:
                logger.error(f"Could not parse recurrence date '{recurrence_end_date_iso}'. Error: {e}")
        
        return event_body

    def list_events(self, time_min_iso: str, time_max_iso: str, filter_by_key: bool = True) -> list[dict]:
        """
        Lists all events in a given time range, handling pagination.

        Args:
            time_min_iso: The minimum start time for events to list.
            time_max_iso: The maximum start time for events to list.
            filter_by_key: If True, only returns events with the 'ptm_event_key'.
                           If False, returns all events in the time range.
        """
        if not self.service:
            return []
        
        all_events = []
        page_token = None
        
        try:
            while True:
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=time_min_iso,
                    timeMax=time_max_iso,
                    singleEvents=True,
                    orderBy='startTime',
                    pageToken=page_token,
                    maxResults=250  # Get up to 250 events per page
                ).execute()
                
                events_on_page = events_result.get('items', [])
                all_events.extend(events_on_page)
                
                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break # Exit loop if we're on the last page
            
            logger.info(f"Fetched a total of {len(all_events)} events from Google Calendar.")

            if filter_by_key:
                # Filter for events that our application owns
                return [
                    event for event in all_events
                    if 'ptm_event_key' in event.get('extendedProperties', {}).get('private', {})
                ]
            else:
                # Return all events for cleanup purposes
                return [
                            event for event in all_events 
                            if event.get('summary', '').startswith("Tuition ")
                        ]

        except Exception as e:
            logger.error(f"Failed to list calendar events: {e}")
            return []

    def create_event(self, event_key: str, summary: str, start_time_iso: str, end_time_iso: str, recurrence_end_date_iso: str | None = None):
        """Creates a new event with our custom key."""
        if not self.service:
            return None

        event_body = self._build_event_body(
            event_key=event_key,
            summary=summary,
            start_time_iso=start_time_iso,
            end_time_iso=end_time_iso,
            recurrence_end_date_iso=recurrence_end_date_iso
        )

        logger.debug(f"Attempting to create event with body: {event_body}")
        try:
            created_event = self.service.events().insert(
                calendarId=self.calendar_id, body=event_body).execute()
            logger.info(f"Created event '{summary}': {created_event.get('htmlLink')}")
            return created_event
        except HttpError as http_err:
            logger.error(f"An HTTP error occurred while creating event '{summary}'.")
            logger.error(f"Status Code: {http_err.resp.status}")
            # The content is bytes, so we decode it for a readable log message
            logger.error(f"Response Body: {http_err.content.decode()}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-HTTP error occurred creating event '{summary}': {e}")
            return None

    def update_event(self, event_id: str, event_key: str, summary: str, start_time_iso: str, end_time_iso: str, recurrence_end_date_iso: str | None = None):
        """Updates an existing event, now with an optional recurrence rule."""
        if not self.service:
            return None
            
        event_body = self._build_event_body(
            event_key=event_key,
            summary=summary,
            start_time_iso=start_time_iso,
            end_time_iso=end_time_iso,
            recurrence_end_date_iso=recurrence_end_date_iso
        )

        logger.debug(f"Attempting to update event {event_id} with body: {event_body}")
        try:
            updated_event = self.service.events().update(
                calendarId=self.calendar_id, eventId=event_id, body=event_body).execute()
            logger.info(f"Updated event '{summary}'.")
            return updated_event
        except HttpError as http_err:
            logger.error(f"An HTTP error occurred while updating event '{summary}'.")
            logger.error(f"Status Code: {http_err.resp.status}")
            # The content is bytes, so we decode it for a readable log message
            logger.error(f"Response Body: {http_err.content.decode()}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected non-HTTP error occurred updating event '{summary}': {e}")
            return None

    def delete_event(self, event_id: str):
        """Deletes an event by its ID."""
        if not self.service:
            return
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id, eventId=event_id).execute()
            logger.info(f"Deleted event ID: {event_id}")
        except HttpError as e:
            # If the event is already gone, that's fine. Ignore the error.
            if e.resp.status == 410:
                logger.warning(f"Attempted to delete event {event_id}, but it was already gone.")
            else:
                logger.error(f"Failed to delete event {event_id}: {e}")

    def delete_all_events(self, events_to_delete):
        for event in events_to_delete:
            self.delete_event(event['google_event_id'])
 
