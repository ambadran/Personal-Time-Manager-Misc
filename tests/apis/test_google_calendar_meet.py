'''

'''

import pytest
from datetime import datetime, timezone, timedelta
import os
from personal_time_manager_misc.apis.google_calendar_meet import GoogleCalendarManager

def test_list_events(google_calendar_manager: GoogleCalendarManager):
    os.chdir("../..")
    print(os.getcwd())
    now_utc = datetime.now(timezone.utc)
    one_week_later_utc = now_utc + timedelta(days=7)

    events = google_calendar_manager.list_events(
                time_min_iso=now_utc.isoformat(),
                time_max_iso=one_week_later_utc.isoformat())
    print(events)


