'''
This file contains all the base models that will be used in the different files
'''
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ScheduledTuition(BaseModel):
    """A Pydantic model representing a scheduled tuition session from the timetable."""
    name: str
    start_time: datetime
    end_time: datetime
    db_tuition_id: str = Field(..., alias='id') # Maps the 'id' key from JSON to this field
    
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    @property
    def zoom_meet_topic(self) -> str:
        """Generates a user-friendly topic name for the Zoom meeting."""
        return self.name.replace('_', ' ')
    
    @property
    def duration_minutes(self) -> int:
        """Calculates the duration of the tuition in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)


