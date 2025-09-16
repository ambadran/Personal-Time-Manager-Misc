'''
The main database handler of this project
'''
import os
import psycopg2
import psycopg2.extensions
import psycopg2.pool
import select
import atexit
import json
from contextlib import contextmanager
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List, Generator, Tuple

from ..common.logger import logger
from ..common.config import DB_EVENT_CHANNEL, MANUAL_TRIGGER_CHANNEL, VALID_RUN_STATUSES

class DatabaseHandler:
    """
    Manages a singleton instance of a PostgreSQL connection pool.
    The handler is self-configuring by loading the DATABASE_URL from the
    .env file upon first initialization.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the connection pool by loading configuration from
        environment variables. This logic only runs once.
        """
        if hasattr(self, 'pool') and self.pool:
            return

        load_dotenv()
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            err_msg = "CRITICAL: DATABASE_URL environment variable is not set."
            logger.critical(err_msg)
            raise ValueError(err_msg)

        try:
            logger.info("Initializing database connection pool...")
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=db_url
            )
            # Only register the cleanup function if NOT running tests
            if "PYTEST_CURRENT_TEST" not in os.environ:
                atexit.register(self.close_pool)
        except psycopg2.OperationalError as e:
            logger.critical(f"FATAL: Could not connect to the database: {e}")
            raise

    def close_pool(self):
        """Closes all connections in the pool."""
        if self.pool:
            logger.info("Closing database connection pool.")
            self.pool.closeall()
            self.pool = None

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """Context manager to get a connection from the pool and release it."""
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def listen_for_notification(self) -> Optional[Tuple[str, Any]]:
        """
        Checks out a connection to listen on multiple channels.
        Returns the channel and payload of the first notification received.
        """
        conn = None
        try:
            conn = self.pool.getconn()
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            
            cursor = conn.cursor()
            cursor.execute(f"LISTEN \"{DB_EVENT_CHANNEL}\";")
            cursor.execute(f"LISTEN \"{MANUAL_TRIGGER_CHANNEL}\";")
            
            logger.info(f"Listening on channels '{DB_EVENT_CHANNEL}' and '{MANUAL_TRIGGER_CHANNEL}'...")
            
            select.select([conn], [], [])
            
            conn.poll()
            if conn.notifies:
                notification = conn.notifies.pop(0)
                logger.info(f"Notification received on channel '{notification.channel}'")
                
                # For DB events, parse the JSON payload
                if notification.channel == DB_EVENT_CHANNEL:
                    payload = json.loads(notification.payload)
                else: # For manual triggers, the payload is just a string
                    payload = notification.payload

                return notification.channel, payload
            return None
        finally:
            if conn:
                self.pool.putconn(conn)

    def fetch_timetable_by_run_id(self, run_id: int) -> Optional[List[Dict[str, Any]]]:
        """Fetches the solution_data JSON from a specific timetable run."""
        sql = "SELECT solution_data FROM timetable_runs WHERE id = %s;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (run_id,))
                    result = cur.fetchone()
                    if result and result[0]:
                        return result[0]
                    else:
                        logger.warning(f"No data found for run_id: {run_id}")
                        return None
        except psycopg2.Error as e:
            logger.error(f"Database error fetching timetable for run_id {run_id}: {e}")
            return None
            
    def fetch_latest_successful_run_id(self) -> Optional[int]:
        """Finds the ID of the most recent 'completed' timetable run."""
        sql = """
            SELECT id FROM timetable_runs 
            WHERE status IN %s AND solution_data IS NOT NULL
            ORDER BY run_started_at DESC 
            LIMIT 1;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Pass the tuple of valid statuses as a parameter
                    cur.execute(sql, (VALID_RUN_STATUSES,))
                    result = cur.fetchone()
                    if result:
                        logger.info(f"Found latest valid run with ID: {result[0]}")
                        return result[0]
                    else:
                        logger.warning("No valid timetable runs found.")
                        return None
        except psycopg2.Error as e:
            logger.error(f"Database error fetching latest valid run: {e}")
            return None

    def fetch_latest_timetable_data(self) -> Optional[List[Dict[str, Any]]]:
        """Fetches the solution_data from the latest successful run."""
        latest_run_id = self.fetch_latest_successful_run_id()
        if latest_run_id:
            return self.fetch_timetable_by_run_id(latest_run_id)
        return None

    def get_all_tuitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetches all tuition records and returns them as a dictionary
        mapped by their UUID for easy lookup.
        """
        logger.info("Fetching all tuition records from the database.")
        tuitions = {}
        sql = "SELECT id, meeting_link FROM tuitions;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    for row in cur.fetchall():
                        tuition_id = str(row[0]) # Convert UUID to string
                        tuitions[tuition_id] = {
                            "id": tuition_id,
                            "meeting_link_data": row[1]
                        }
            return tuitions
        except psycopg2.Error as e:
            logger.error(f"Database error fetching all tuitions: {e}")
            return {}

    def update_tuition_meeting_link(self, tuition_id: str, meeting_data: Dict[str, Any]) -> bool:
        """
        Updates the meeting_link JSONB for a specific tuition record.
        """
        sql = "UPDATE tuitions SET meeting_link = %s WHERE id = %s;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # psycopg2 can automatically convert a Python dict to a JSONB string
                    cur.execute(sql, (json.dumps(meeting_data), tuition_id))
                conn.commit()
            logger.info(f"Successfully updated meeting link for tuition ID: {tuition_id}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to update meeting link for tuition ID {tuition_id}: {e}")
            return False

    def get_all_calendar_events(self) -> List[Dict[str, Any]]:
        """Fetches all records from the calendar_events table."""
        events = []
        sql = "SELECT id, timetable_run_id, event_key, google_event_id FROM calendar_events;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    for row in cur.fetchall():
                        events.append({
                            "id": row[0],
                            "timetable_run_id": row[1],
                            "event_key": row[2],
                            "google_event_id": row[3]
                        })
            return events
        except psycopg2.Error as e:
            logger.error(f"Database error fetching all calendar events: {e}")
            return []

    def clear_calendar_events(self) -> bool:
        """
        Deletes all records from the calendar_events table.
        TRUNCATE is faster and resets the ID sequence.
        """
        sql = "TRUNCATE TABLE calendar_events RESTART IDENTITY;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            logger.info("Successfully cleared the calendar_events table.")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to clear calendar_events table: {e}")
            return False

    def save_calendar_event_mapping(self, run_id: int, event_key: str, google_event_id: str) -> bool:
        """Saves a new mapping between a timetable event and a Google Calendar event."""
        sql = """
            INSERT INTO calendar_events (timetable_run_id, event_key, google_event_id)
            VALUES (%s, %s, %s);
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (run_id, event_key, google_event_id))
                conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to save calendar event mapping for key {event_key}: {e}")
            return False

    def clear_all_tuition_meeting_links(self) -> bool:
        """Sets the meeting_link column to NULL for all records in the tuition table."""
        logger.info("Clearing all meeting links from the tuition table.")
        sql = "UPDATE tuitions SET meeting_link = NULL;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            logger.info("Successfully cleared tuition meeting links.")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to clear tuition meeting links: {e}")
            return False

