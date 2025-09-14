import os
import psycopg2
import pytest
from dotenv import load_dotenv
from personal_time_manager_misc.database.db_handler import DatabaseHandler
from personal_time_manager_misc.apis.google_calendar_meet import GoogleCalendarManager
from personal_time_manager_misc.apis.zoom_meeting import ZoomMeetingManager

@pytest.fixture
def zoom_meeting_manager() -> ZoomMeetingManager:
    return ZoomMeetingManager()

@pytest.fixture
def db_handler() -> DatabaseHandler:
    """Provides a fresh DatabaseHandler instance for each test."""
    return DatabaseHandler()

@pytest.fixture
def google_calendar_manager() -> GoogleCalendarManager:
    os.chdir("../..")
    return GoogleCalendarManager()

#TODO: finish this
@pytest.fixture(scope="function")
def test_db_session():
    """
    A pytest fixture that provides a database connection to the test DB,
    inserts a test record, yields control to the test, and then cleans up
    by deleting the record.
    """
    load_dotenv()
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.fail("TEST_DATABASE_URL is not set in the .env file.")

    conn = psycopg2.connect(test_db_url)
    cursor = conn.cursor()
    
    inserted_id = None
    try:
        # 1. SETUP: Insert a test record and get its ID
        sql_insert = """
            INSERT INTO timetable_runs (run_started_at, status, input_version_hash, solution_data)
            VALUES (NOW(), 'completed', 'e2e_test_record', '{"name": "E2E Test"}'::jsonb)
            RETURNING id;
        """
        cursor.execute(sql_insert)
        inserted_id = cursor.fetchone()[0]
        conn.commit()
        
        # 2. YIELD: Pass the ID to the test function
        yield inserted_id
        
    finally:
        # 3. TEARDOWN: Clean up the record after the test is done
        if inserted_id:
            cursor.execute("DELETE FROM timetable_runs WHERE id = %s;", (inserted_id,))
            conn.commit()
        cursor.close()
        conn.close()
