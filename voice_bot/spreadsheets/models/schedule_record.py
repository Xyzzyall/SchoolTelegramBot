from dataclasses import dataclass
from datetime import date


@dataclass
class ScheduleRecord:
    user_id: str
    is_online: bool
    day_of_the_week: int
    time_start: str
    time_end: str
    absolute_start_date: date | None = None
    description: str = ""



