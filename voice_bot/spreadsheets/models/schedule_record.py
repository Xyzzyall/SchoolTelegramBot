from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class ScheduleRecord:
    user_id: str
    is_online: bool
    day_of_the_week: int
    time_start: str
    time_end: str
    absolute_start_date: datetime | None = None
    description: str = ""



