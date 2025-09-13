'''
main entry point of this background worker
Contains and executes the Main Routine
'''
import time
import psycopg2
import sys
from personal_time_manager_misc.database.db_handler import DatabaseHandler
from personal_time_manager_misc.common.logger import logger
from personal_time_manager_misc.core.main_handler import HandleTimeTable

def main_routine():
    """
    The main background worker routine.
    """
    logger.info("Personal Time Manager MISC Worker is starting...")
    
    try:
        db_handler = DatabaseHandler()
    except (ValueError, psycopg2.OperationalError) as e:
        logger.critical(f"Worker failed to start due to database initialization error: {e}")
        sys.exit(1)
        return

    try:
        while True:
            notification = db_handler.listen_for_notification()
            if notification:
                # When a trigger is detected, instantiate the main handler
                # to orchestrate all the necessary tasks.
                HandleTimeTable(db_handler, *notification)
            
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Worker shutting down gracefully due to user request (Ctrl+C).")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in the main loop: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_routine()
