'''
This file is responsible to create the Zoom tuition meetings
'''
from datetime import datetime
from dateutil.parser import isoparse

from ..database.db_handler import DatabaseHandler
from ..apis.zoom_meeting import ZoomMeetingManager
from ..common.logger import logger
from ..common.config import RECURRENCE_END_DATE_ISO
from .base_classes import ScheduledTuition

class HandleTuitionMeetings:
    '''
    This class will create / update / delete the current Zoom meeting events in both:
    - the Zoom API (personal email)
    - The meeting_link column of the tuition table in the database
    '''
    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler
        self.zoom_manager = ZoomMeetingManager()
        self.scheduled_tuitions: list[ScheduledTuition] = []
        self.existing_tuitions: dict[str, dict] = {}

        # run the full sync 
        self.run_sync()

    def _fetch_data(self):
        """Fetches latest timetable and all existing tuition data from the database."""
        logger.info("Fetching required data from database...")
        timetable_data = self.db_handler.fetch_latest_timetable_data()
        self.existing_tuitions = self.db_handler.get_all_tuitions()

        if not timetable_data:
            logger.warning("No timetable data found. Aborting sync.")
            return False
        
        self.timetable_data = timetable_data
        return True

    def _match_and_prepare(self):
        """
        Filters timetable for tuitions and validates them into ScheduledTuition objects.
        """
        logger.info("Matching scheduled times to tuition records...")
        for event in self.timetable_data:
            if event.get("category") == "Tuition" and "id" in event:
                try:
                    # Convert string times to datetime objects
                    event['start_time'] = isoparse(event['start_time'])
                    event['end_time'] = isoparse(event['end_time'])
                    
                    # Validate and create a Pydantic object
                    scheduled_item = ScheduledTuition(**event)
                    self.scheduled_tuitions.append(scheduled_item)
                except Exception as e:
                    logger.error(f"Could not parse tuition event '{event.get('name')}'. Error: {e}")
        
        logger.info(f"Successfully prepared {len(self.scheduled_tuitions)} tuition sessions for sync.")

    def _sync_meetings(self):
        """
        Implements the 'Create -> Update DB -> Delete Old' sync strategy.
        """
        if not self.scheduled_tuitions:
            logger.info("No scheduled tuitions to sync.")
            return

        logger.info("Starting sync for each scheduled tuition...")
        for tuition in self.scheduled_tuitions:
            logger.info(f"Processing: {tuition.zoom_meet_topic}")
            try:
                # Step 1: Create the new Zoom meeting
                creation_result = self.zoom_manager.create_meeting(
                    topic=tuition.zoom_meet_topic,
                    start_time_iso=tuition.start_time.isoformat(),
                    duration_minutes=tuition.duration_minutes,
                    recurrence_end_date_iso=RECURRENCE_END_DATE_ISO
                )
                if not creation_result:
                    logger.error(f"Failed to create Zoom meeting for '{tuition.zoom_meet_topic}'. Skipping.")
                    continue
                
                meeting_id, join_url = creation_result
                new_meeting_data = {'meeting_link': join_url, 'meeting_id': str(meeting_id)}
                
                # Step 2: Update the database with the new meeting link
                update_success = self.db_handler.update_tuition_meeting_link(
                    tuition_id=tuition.db_tuition_id,
                    meeting_data=new_meeting_data
                )

                if not update_success:
                    logger.error(f"DB update failed for '{tuition.zoom_meet_topic}'. The new Zoom meeting was still created.")
                    continue

                # Step 3: Delete the old Zoom meeting (if one existed)
                old_tuition_data = self.existing_tuitions.get(tuition.db_tuition_id)
                if old_tuition_data and old_tuition_data.get('meeting_link_data'):
                    old_meeting_id = old_tuition_data['meeting_link_data'].get('meeting_id')
                    if old_meeting_id:
                        logger.info(f"Deleting old Zoom meeting (ID: {old_meeting_id})")
                        try:
                            self.zoom_manager.delete_meeting(old_meeting_id)
                        except Exception as e:
                            logger.error(f"Failed to delete old Zoom meeting {old_meeting_id}. It may need manual deletion. Error: {e}")

            except Exception as e:
                logger.exception(f"An unexpected error occurred while syncing '{tuition.zoom_meet_topic}': {e}")

    def run_sync(self):
        """The main public method to orchestrate the entire sync process."""
        logger.info("Starting tuition meeting sync process...")
        if self._fetch_data():
            self._match_and_prepare()
            self._sync_meetings()
        logger.info("Tuition meeting sync process finished.")
