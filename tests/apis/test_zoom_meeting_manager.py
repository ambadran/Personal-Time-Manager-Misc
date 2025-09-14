'''

'''
import pytest
from datetime import datetime, timezone, timedelta
import os
from personal_time_manager_misc.apis.zoom_meeting import ZoomMeetingManager

def test_nuke_all_meetings(zoom_meeting_manager: ZoomMeetingManager):
    zoom_meeting_manager.delete_all_automated_tuition_meetings()

