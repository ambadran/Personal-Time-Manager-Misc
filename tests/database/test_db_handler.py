'''

'''
import pytest
from unittest.mock import MagicMock

# A trick to allow imports from the 'src' directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from personal_time_manager_misc.database.db_handler import DatabaseHandler

# def test_database_handler_initialization(mocker):
#     """
#     Tests that the DatabaseHandler initializes correctly by mocking external dependencies.
#     """
#     # 1. Mock all external dependencies
#     mocker.patch('dotenv.load_dotenv') # Mock environment file loading
#     mock_getenv = mocker.patch('os.getenv', return_value='fake_db_url') # Mock reading the URL
#     mock_pool = mocker.patch('psycopg2.pool.SimpleConnectionPool') # Mock the actual connection pool

#     # 2. Instantiate the handler
#     # The singleton pattern means we need to clear the instance for a clean test
#     DatabaseHandler._instance = None 
#     db_handler = DatabaseHandler()

#     # 3. Assert that our mocks were called as expected
#     mock_getenv.assert_called_once_with("DATABASE_URL")
#     mock_pool.assert_called_once_with(min_conn=1, max_conn=5, dsn='fake_db_url')
    
#     assert isinstance(db_handler, DatabaseHandler)

# def test_database_handler_singleton(mocker):
#     """
#     Tests that the singleton pattern works correctly.
#     """
#     mocker.patch('dotenv.load_dotenv')
#     mocker.patch('os.getenv', return_value='fake_db_url')
#     mock_pool_constructor = mocker.patch('psycopg2.pool.SimpleConnectionPool')

#     # Instantiate it twice
#     DatabaseHandler._instance = None
#     handler1 = DatabaseHandler()
#     handler2 = DatabaseHandler()

#     # Assert the constructor was only called once and we have the same object
#     mock_pool_constructor.assert_called_once()
#     assert handler1 is handler2

def delete_latest_calendar_event(db_handler) -> bool:
        """Deletes the most recent entry from the calendar_events table."""
        # Assumes a 'created_at' column exists for ordering.
        sql = "DELETE FROM calendar_events WHERE id = (SELECT id FROM calendar_events ORDER BY created_at DESC LIMIT 1);"
        try:
            with db_handler.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                # Note: commit is called on the connection object outside the cursor context
                conn.commit()
            print("successfully deleted the last test record")
            return True
        except psycopg2.Error as e:
            # In a real app, you'd use a logger.
            # logger.error(f"Database error deleting latest calendar event: {e}")
            print(f"Database error deleting latest calendar event: {e}") # Simulating logging for the test
            return False

def test_calendar_events(db_handler):
    db_handler.save_calendar_event_mapping(15, 'testkey', 'testgoogle')
    print(db_handler.get_all_calendar_events())
    delete_latest_calendar_event(db_handler)

def test_save_meeting_link(db_handler):
    #TODO: WHY IS THIS THING NOT WORKING!!!!!!!
    pass

# def test_tmp(db_handler):
#     db_handler.clear_calendar_events()


