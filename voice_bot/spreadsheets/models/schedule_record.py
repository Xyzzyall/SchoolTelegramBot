from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScheduleRecord:
    user_id: str
    is_online: bool
    day_of_the_week: str
    time_start: datetime
    time_end: datetime
    description: str = ""
