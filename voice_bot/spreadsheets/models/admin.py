from dataclasses import dataclass
from datetime import timedelta


@dataclass
class Admin:
    telegram_login: str

    lesson_reminders: list[timedelta]

