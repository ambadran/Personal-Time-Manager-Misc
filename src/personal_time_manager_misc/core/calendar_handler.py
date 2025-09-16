'''
This file is responsible to create and sync all calendar events

for now, the only calendar I need to worry about is the google calendar which should sync with the apple calendar automatically
'''
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

    def run_sync(self):
        logger.info("Starting Google Calendar sync with smart cleanup strategy...")

        # --- STEP 1: CLEAR ALL EXISTING EVENTS ---
        # This single call now handles finding and deleting all unique event series from Google Calendar.
        self.calendar_manager.delete_all_automated_tuition_events()
        
        # We still need to clear our local mapping table to match the clean slate.
        self.db_handler.clear_calendar_events()

        # --- STEP 2: FETCH AND CREATE NEW EVENTS ---
        latest_run_id = self.db_handler.fetch_latest_successful_run_id()
        if not latest_run_id:
            logger.warning("No valid timetable run found. Aborting sync.")
            return
            
        timetable_data = self.db_handler.fetch_timetable_by_run_id(latest_run_id)
        if not timetable_data:
            logger.warning("Timetable data is empty. Aborting sync.")
            return

        tuition_events = [
            event for event in timetable_data if event.get("category") == "Tuition"
        ]
        logger.info(f"Found {len(tuition_events)} 'Tuition' events in the latest timetable to create.")

        target_tz = timezone(DEFAULT_TIMEZONE)
        
        for event in tuition_events:
            try:
                # Prepare timezone-aware timestamps
                start_dt_naive = isoparse(event.get("start_time"))
                end_dt_naive = isoparse(event.get("end_time"))
                start_dt_aware = target_tz.localize(start_dt_naive)
                end_dt_aware = target_tz.localize(end_dt_naive)
                
                event_key = self._generate_event_key(event)
                summary = event['name'].replace('_', ' ')
                
                # Create the new recurring event
                created_event = self.calendar_manager.create_event(
                    event_key=event_key,
                    summary=summary,
                    start_time_iso=start_dt_aware.isoformat(),
                    end_time_iso=end_dt_aware.isoformat(),
                    recurrence_end_date_iso=RECURRENCE_END_DATE_ISO
                )

                # If creation succeeds, save the mapping to our local DB
                if created_event and 'id' in created_event:
                    google_event_id = created_event['id']
                    self.db_handler.save_calendar_event_mapping(
                        run_id=latest_run_id,
                        event_key=event_key,
                        google_event_id=google_event_id
                    )
            except Exception as e:
                logger.exception(f"An error occurred while creating event '{event.get('name')}'. Skipping.")
                
        logger.info("Google Calendar sync finished successfully.")
