from datetime import datetime, date, timedelta

import pytz
from injector import singleton, inject

from voice_bot.constants import DAYS_OF_THE_WEEK


def cut_timezone(dt: datetime) -> datetime:
    return datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute, second=dt.second)


def to_midnight(dt: datetime) -> datetime:
    return dt - timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)


def to_day_end(dt: datetime) -> datetime:
    return to_midnight(dt) + timedelta(hours=23, minutes=59, seconds=59)


def dt_fmt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%y")


def dt_fmt_rus(dt: datetime) -> str:
    return f"{DAYS_OF_THE_WEEK[dt.weekday() + 1]} ({dt_fmt(dt)})"


def dt_fmt_week(monday: datetime) -> str:
    return f"{dt_fmt(monday)}-{dt_fmt(monday + timedelta(days=6))}"


def day_with_str_hours(day: datetime, time: str) -> datetime:
    split = time.split(":")
    return to_midnight(day) + timedelta(hours=int(split[0]), minutes=int(split[1]))


def str_hours_from_dt(dt: datetime) -> str:
    return f"{dt.hour:02d}:{dt.minute:02d}"


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

    def dt_now_monday(self) -> datetime:
        now = to_midnight(self.now())
        return now - timedelta(days=now.weekday())
