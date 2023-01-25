from dataclasses import dataclass
from datetime import timedelta


@dataclass
class User:
    row_id: int
    unique_id: str
    telegram_login: str
    fullname: str
    secret_code: str

    schedule_reminders: set[timedelta]

