from datetime import datetime, date

import pytz
from injector import singleton, inject


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
