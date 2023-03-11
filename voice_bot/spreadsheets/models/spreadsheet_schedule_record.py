from dataclasses import dataclass
from datetime import datetime


@dataclass
class SpreadsheetScheduleRecord:
    table_name: str | None

    user_id: str
    is_online: bool
    day_of_the_week: int
    raw_time_start_time_end: str
    time_start: str
    time_end: str
    absolute_start_time: datetime | None = None
    description: str = ""
    to_delete: bool = False



