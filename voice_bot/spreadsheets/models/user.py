from dataclasses import dataclass
from datetime import timedelta


@dataclass
class User:
    unique_id: str
    telegram_login: str
    fullname: str

    schedule_reminders: list[timedelta]

