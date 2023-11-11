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


def to_monday_midnight(dt: datetime) -> datetime:
    return to_midnight(dt) - timedelta(days=dt.weekday())


def dt_fmt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%y")


def dt_fmt_time(dt: datetime) -> str:
    return dt.strftime("%d.%m.%y %H:%M")


def dt_fmt_rus(dt: datetime) -> str:
    return f"{DAYS_OF_THE_WEEK[dt.weekday() + 1]} ({dt_fmt(dt)})"


def dt_fmt_week(monday: datetime) -> str:
    return f"{dt_fmt(monday)}-{dt_fmt(monday + timedelta(days=6))}"


def day_with_str_hours(day: datetime, time: str) -> datetime:
    split = time.split(":")
    return to_midnight(day) + timedelta(hours=int(split[0]), minutes=int(split[1]))


def td_days_and_str_hours(days: int, time: str) -> timedelta:
    split = time.split(":")
    return timedelta(days=days, hours=int(split[0]), minutes=int(split[1]))


def str_hours_from_dt(dt: datetime) -> str:
    return f"{dt.hour:02d}:{dt.minute:02d}"


def str_timedelta_days(days: int, dt: datetime) -> str:
    match days:
        case 0:
            return f"Сегодня {dt_fmt_rus(dt)}"
        case 1:
            return f"Завтра {dt_fmt_rus(dt)}"
        case 2:
            return f"Послезавтра {dt_fmt_rus(dt)}"
        case 3 | 4:
            return f"Через {days} дня {dt_fmt_rus(dt)}"
        case _:
            return f"Через {days} дней {dt_fmt_rus(dt)}"


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
