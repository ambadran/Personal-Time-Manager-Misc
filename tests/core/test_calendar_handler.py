'''
This file will auto-test the tuition meeting functionality
'''
import pytest
from datetime import datetime, timedelta
from pytz import timezone
from dateutil.parser import isoparse # Make sure to have python-dateutil installed
import os
from personal_time_manager_misc.database.db_handler import DatabaseHandler
from personal_time_manager_misc.apis.google_calendar_meet import GoogleCalendarManager
from personal_time_manager_misc.common.config import RECURRENCE_END_DATE_ISO
from pprint import pp as pprint



def test_delete_all_events(google_calendar_manager: GoogleCalendarManager, db_handler: DatabaseHandler):
    do_i_really_want_to_do_it = True
    if do_i_really_want_to_do_it:
        events_to_delete = db_handler.get_all_calendar_events()
        print(events_to_delete)
        google_calendar_manager.delete_all_events(events_to_delete)
        db_handler.clear_calendar_events()

#TODO should import HandleTuitionGoogleCalendarEvent
def _generate_event_key(event: dict) -> str:
    """Creates a stable, unique key for an event from the timetable."""
    # For tuitions, the UUID is the perfect unique key.
    if event.get("category") == "Tuition" and "id" in event:
        return f"ptm-tuition-{event['id']}"
    # For other events, we can use the name and start time.
    return f"ptm-event-{event['name']}-{event['start_time']}"


def test_create_event(google_calendar_manager: GoogleCalendarManager, db_handler: DatabaseHandler):

        latest_run_id = db_handler.fetch_latest_successful_run_id()
        if not latest_run_id:
            pritn("No valid timetable run found. Aborting sync.")
            return
            
        timetable_data = db_handler.fetch_timetable_by_run_id(latest_run_id)
        if not timetable_data:
            print("Timetable data is empty. Aborting sync.")
            return

        # 2b. Filter for 'Tuition' events only
        tuition_events = [
            event for event in timetable_data if event.get("category") == "Tuition"
        ]
        pprint(tuition_events)

        event = tuition_events[0]

       
        # --- FIX STARTS HERE ---
        cairo_tz = timezone("Africa/Cairo")
        # 1. Parse the naive time strings from your database
        start_dt_naive = isoparse(event.get("start_time"))
        end_dt_naive = isoparse(event.get("end_time"))
        
        # 2. Make them "aware" by explicitly attaching the Cairo timezone
        start_dt_aware = cairo_tz.localize(start_dt_naive)
        end_dt_aware = cairo_tz.localize(end_dt_naive)
        
        # 3. Convert them back to a full ISO 8601 string with the offset
        # This will produce strings like '2025-09-13T15:00:00+03:00'
        start_time_iso_aware = start_dt_aware.isoformat()
        end_time_iso_aware = end_dt_aware.isoformat()
        # --- FIX ENDS HERE ---

        event_key = _generate_event_key(event)
        summary = event['name'].replace('_', ' ')
        print(event, event_key, summary)

        # Create the event in Google Calendar
        created_event = google_calendar_manager.create_event(
            event_key=event_key,
            summary=summary,
            start_time_iso=start_time_iso_aware,
            end_time_iso=end_time_iso_aware,
            recurrence_end_date_iso=RECURRENCE_END_DATE_ISO
        )
        print("Created Event:\n")
        pprint(created_event)

        # If creation was successful, save the new mapping to our DB
        if created_event and 'id' in created_event:
            google_event_id = created_event['id']
            db_handler.save_calendar_event_mapping(
                run_id=latest_run_id,
                event_key=event_key,
                google_event_id=google_event_id
            )




