'''
This file initiates and executes everything when a new timetable run is passed successfully
'''
from ..database.db_handler import DatabaseHandler
from ..common.logger import logger
from .tuition_meeting import HandleTuitionMeetings
from .calendar_handler import HandleTuitionGoogleCalendarEvents

class HandleTimeTable:
    """
    Deploys all the logic for a new successful timetable. This class is the
    main orchestrator for the worker's tasks.
    """
    def __init__(self, db_handler: DatabaseHandler, channel: str, payload: any):
        self.db_handler = db_handler
        self.channel = channel
        self.payload = payload
        self.is_valid_trigger = False

        # Step 1: Check if the trigger corresponds to a successful run.
        self._validate_trigger()

        if not self.is_valid_trigger:
            logger.warning("Trigger is not for a valid, completed timetable run. Halting process.")
            return
        
        logger.info("Valid trigger detected. Starting sync processes...")
        
        # Step 2: Run Tuition Meeting sync
        logger.warning("\nSKIPPING ZOOM TUITION..\n")
        # try:
        #     HandleTuitionMeetings(self.db_handler)
        # except Exception as e:
        #     logger.exception(f"An error occurred during the tuition sync process: {e}")

        # Step 3: Google Calendar (Placeholder)
        try:
            HandleTuitionGoogleCalendarEvents(self.db_handler)
        except Exception as e:
            logger.exception(f"An error occurred during the Google Calendar sync process: {e}")

        # Step 4: Apple Calendar (Placeholder)
        # logger.info("Apple Calendar sync would run here.")

    def _validate_trigger(self):
        """
        Checks if the received notification points to a 'completed' run.
        This prevents processing of failed or in-progress runs.
        """
        latest_run_id = self.db_handler.fetch_latest_successful_run_id()
        if latest_run_id is not None:
             self.is_valid_trigger = True
