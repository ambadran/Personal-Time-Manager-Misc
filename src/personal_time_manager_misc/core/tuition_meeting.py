'''
This file is responsible to create the Zoom tuition meetings
'''
from dateutil.parser import isoparse
from ..database.db_handler import DatabaseHandler
from ..common.logger import logger
from ..apis.zoom_meeting import ZoomMeetingManager
from ..common.config import RECURRENCE_END_DATE_ISO
from .base_classes import ScheduledTuition

class HandleTuitionZoomMeetings:
    """
    Handles syncing tuition meetings to Zoom using a "clear and replace" strategy.
    """
    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler
        self.zoom_manager = ZoomMeetingManager()
        self.run_sync()

    def run_sync(self):
        logger.info("Starting Zoom meeting sync with 'clear and replace' strategy...")
        
        # --- STEP 1: NUKE ALL EXISTING ZOOM MEETINGS ---
        self.zoom_manager.delete_all_automated_tuition_meetings()

        # --- STEP 2: DELETE MEETING LINKS FROM DB ---
        self.db_handler.clear_all_tuition_meeting_links()

        # --- STEP 3: CREATE NEW MEETINGS AND SAVE TO DB ---
        timetable_data = self.db_handler.fetch_latest_timetable_data()
        if not timetable_data:
            logger.warning("No timetable data found. Aborting Zoom sync.")
            return

        tuition_events = [e for e in timetable_data if e.get("category") == "Tuition" and "id" in e]
        logger.info(f"Found {len(tuition_events)} tuition events in the timetable to process.")
        
        for event_data in tuition_events:
            try:
                event_data['start_time'] = isoparse(event_data['start_time'])
                event_data['end_time'] = isoparse(event_data['end_time'])
                tuition = ScheduledTuition(**event_data)
                
                # Create the new meeting on Zoom
                creation_result = self.zoom_manager.create_meeting(
                    topic=tuition.zoom_meet_topic,
                    start_time_iso=tuition.start_time.isoformat(),
                    duration_minutes=tuition.duration_minutes,
                    recurrence_end_date_iso=RECURRENCE_END_DATE_ISO
                )

                # If successful, save the new link to the database
                if creation_result:
                    meeting_id, join_url = creation_result
                    new_meeting_data = {'meeting_link': join_url, 'meeting_id': str(meeting_id)}
                    self.db_handler.update_tuition_meeting_link(
                        tuition_id=tuition.db_tuition_id,
                        meeting_data=new_meeting_data
                    )
            except Exception as e:
                logger.exception(f"Failed to process tuition event '{event_data.get('name')}'. Skipping.")

        logger.info("Zoom meeting sync process finished successfully.")
