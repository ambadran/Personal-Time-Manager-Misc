'''
THis script tests if the notificaiton sending and receiving logic is functional
'''
import pytest
import threading
import time

# A trick to allow imports from the 'src' directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from personal_time_manager_misc.__main__ import main_routine
from personal_time_manager_misc.database.db_handler import DatabaseHandler

#TODO: this test is pending me to create the postegres test database using docker
# Mark this as an 'e2e' test so you can run it separately if needed
# meaning I can do `pytest -m e2e`
@pytest.mark.e2e
def test_main_routine_detects_db_insert(test_db_session, caplog, monkeypatch):
    """
    An end-to-end test to verify that the main_routine running in a thread
    detects a real database insert.
    """
    # Use monkeypatch to force the DatabaseHandler to use the TEST database URL
    # This ensures the worker connects to the same DB as the test fixture
    test_db_url = os.getenv("TEST_DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    
    # The fixture `test_db_session` has already inserted a record.
    # Its ID is passed into this test function.
    new_run_id = test_db_session
    
    # Run the main_routine in a background thread
    worker_thread = threading.Thread(target=main_routine, daemon=True)
    worker_thread.start()
    
    # Give the worker a moment to start and connect
    time.sleep(2)

    # Poll the logs for up to 5 seconds to see if our message appears
    success = False
    for _ in range(5):
        if f"New timetable run detected with ID: {new_run_id}" in caplog.text:
            success = True
            break
        time.sleep(1)
        
    # Assert that the worker successfully logged the detection
    assert success, f"Worker did not detect new timetable run with ID {new_run_id} within 5 seconds."
    
    # Clean up singleton instance to not affect other tests
    DatabaseHandler._instance = None
