from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class SpreadsheetUser:
    row_id: int
    unique_id: str
    telegram_login: str
    fullname: str
    secret_code: str

    schedule_reminders: set[timedelta]

    chat_id: str = ''

    roles: list[str] = field(default_factory=list)

    to_delete: bool = False
