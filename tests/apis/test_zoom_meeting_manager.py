'''

'''
import pytest
from datetime import datetime, timezone, timedelta
import os
from personal_time_manager_misc.apis.zoom_meeting import ZoomMeetingManager

def test_list_meetings(zoom_meeting_manager: ZoomMeetingManager):
    all_meetings = zoom_meeting_manager.list_meetings()
    print(all_meetings)
    print(len(all_meetings))

def test_list_unique_meetings(zoom_meeting_manager: ZoomMeetingManager):
    all_meetings = zoom_meeting_manager.list_unique_meetings()
    print(all_meetings)
    print(len(all_meetings))



def test_delete_all_meetings(zoom_meeting_manager: ZoomMeetingManager):
    zoom_meeting_manager.delete_all_automated_tuition_meetings()

