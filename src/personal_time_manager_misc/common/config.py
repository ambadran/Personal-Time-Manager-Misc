'''
Configuration constants for the application
'''
# Channel for automatic notifications from the timetable_runs table trigger
DB_EVENT_CHANNEL = "timetable_run_changed"

# Channel for manual trigger requests from other services
MANUAL_TRIGGER_CHANNEL = "manual-ptm-misc-trigger"

# The end date for recurring Zoom meetings. Format is ISO 8601.
RECURRENCE_END_DATE_ISO = "2026-01-31T23:59:59Z"

# A tuple of run_status_enum values that are considered valid for processing
VALID_RUN_STATUSES = ("SUCCESS", "MANUAL")

# The default timezone for creating calendar events. (IANA format)
DEFAULT_TIMEZONE = "Africa/Cairo"
