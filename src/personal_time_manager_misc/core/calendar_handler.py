'''
This file is responsible to create and sync all calendar events

for now, the only calendar I need to worry about is the google calendar which should sync with the apple calendar automatically
'''
from datetime import datetime
from datetime import timezone as timezone_dt
from dateutil.parser import isoparse
from pytz import timezone
from ..database.db_handler import DatabaseHandler
from ..common.logger import logger
from ..apis.google_calendar_meet import GoogleCalendarManager
from ..common.config import RECURRENCE_END_DATE_ISO, DEFAULT_TIMEZONE

class HandleTuitionGoogleCalendarEvents:
    """
    Placeholder class for handling Google Calendar sync logic.
    For now, it will simply create events for all timetable items.
    """
    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler

        self.calendar_manager = GoogleCalendarManager()
        if not self.calendar_manager.service:
            logger.critical(f"Failed to initiate google api instance!")
            return None

        self.run_sync()

    def _generate_event_key(self, event: dict) -> str:
        """Creates a stable, unique key for a tuition event from the timetable."""
        return f"ptm-tuition-{event['id']}"

    def clean_up_prev_tuition_events(self):
        try:
            logger.info("Starting Clean up routine...")
            # 1a. Fetch all event mappings we have stored
            # events_to_delete = self.db_handler.get_all_calendar_events()
            # logger.info(f"Found {len(events_to_delete)} existing calendar events to delete.")
            # 1. Define a wide time range to find all possible events
            time_min_iso = datetime.now(timezone_dt.utc).isoformat()
            time_max_iso = RECURRENCE_END_DATE_ISO
            
            # 2. List all events created by our app within that range
            events_to_delete = self.calendar_manager.list_events(
                time_min_iso=time_min_iso, 
                time_max_iso=time_max_iso,
                filter_by_key=False 
            )
            if not events_to_delete:
                logger.info("No application-created events were found in the calendar.")
                return

            logger.warning(f"Found {len(events_to_delete)} events that will be permanently deleted.")
            
            # 1b. Delete each event from Google Calendar
            deleted_count = 0
            for ind, event_data in enumerate(events_to_delete):
                event_id = event_data['id']
                summary = event_data.get('summary', 'Untitled Event')
                logger.info(f"Deleting event ({ind}/{len(events_to_delete)}): '{summary}' (ID: {event_id})")
                self.calendar_manager.delete_event(event_id)
                deleted_count += 1
                
            logger.info(f"Cleanup complete. Successfully deleted {deleted_count} events.")

        except Exception as e:
            logger.critical(f"The cleanup script failed with an error:\n{e}")
            return False
           
        # 1c. Clear our mapping table completely
        self.db_handler.clear_calendar_events()
        return True


    def run_sync(self):
        logger.info("Starting Google Calendar sync with 'clear and replace' strategy...")

        # --- STEP 1: CLEAR ALL EXISTING EVENTS ---
        if not self.clean_up_prev_tuition_events():
            return
        
        # --- STEP 2: FETCH AND FILTER NEW TIMETABLE DATA ---
        
        # 2a. Get the full timetable from the latest successful run
        latest_run_id = self.db_handler.fetch_latest_successful_run_id()
        if not latest_run_id:
            logger.warning("No valid timetable run found. Aborting sync.")
            return
            
        timetable_data = self.db_handler.fetch_timetable_by_run_id(latest_run_id)
        if not timetable_data:
            logger.warning("Timetable data is empty. Aborting sync.")
            return

        # 2b. Filter for 'Tuition' events only
        tuition_events = [
            event for event in timetable_data if event.get("category") == "Tuition"
        ]
        logger.info(f"Found {len(tuition_events)} 'Tuition' events in the latest timetable to create.")

        # --- STEP 3: CREATE NEW EVENTS AND SAVE MAPPINGS ---

        # Define the target timezone once
        target_tz = timezone(DEFAULT_TIMEZONE)
        success_count = 0
        fail_count = 0
        for event in tuition_events:
            try:

                # 1. Parse the naive time strings from your database
                start_dt_naive = isoparse(event.get("start_time"))
                end_dt_naive = isoparse(event.get("end_time"))
                
                # 2. Make them "aware" by explicitly attaching the Cairo timezone
                start_dt_aware = target_tz.localize(start_dt_naive)
                end_dt_aware = target_tz.localize(end_dt_naive)
                
                # 3. Convert them back to a full ISO 8601 string with the offset
                # This will produce strings like '2025-09-13T15:00:00+03:00'
                start_time_iso_aware = start_dt_aware.isoformat()
                end_time_iso_aware = end_dt_aware.isoformat()

                event_key = self._generate_event_key(event)
                summary = event['name'].replace('_', ' ')
                
                # Create the event in Google Calendar
                created_event = self.calendar_manager.create_event(
                    event_key=event_key,
                    summary=summary,
                    start_time_iso=start_time_iso_aware,
                    end_time_iso=end_time_iso_aware,
                    recurrence_end_date_iso=RECURRENCE_END_DATE_ISO
                )

                # If creation was successful, save the new mapping to our DB
                if created_event and 'id' in created_event:
                    success_count += 1
                    google_event_id = created_event['id']
                    self.db_handler.save_calendar_event_mapping(
                        run_id=latest_run_id,
                        event_key=event_key,
                        google_event_id=google_event_id
                    )
                else:
                    fail_count += 1
            except Exception as e:
                logger.exception(f"An error occurred while creating event '{event.get('name')}'. Skipping.")
                
        logger.info(f"Google Calendar 'clear and replace' sync finished.\nSuccessfully create: {success_count} Tuition Events.\nFailed to create: {fail_count} Tuition Events.")
