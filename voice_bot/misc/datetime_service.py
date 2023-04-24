from datetime import datetime, date, timedelta

import pytz
from injector import singleton, inject


def cut_timezone(dt: datetime):
    return datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute, second=dt.second)


def to_midnight(dt: datetime):
    return dt - timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)


@singleton
class DatetimeService:
    @inject
    def __init__(self):
        self.timezone = pytz.timezone('Europe/Moscow')  # todo: move to configs

    def now(self) -> datetime:
        now = datetime.now(tz=self.timezone)
        return datetime(year=now.year, month=now.month, day=now.day, hour=now.hour, minute=now.minute, second=now.second)

    def today(self) -> date:
        return self.now().today()
