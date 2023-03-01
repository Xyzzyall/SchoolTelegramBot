from dataclasses import dataclass
from datetime import timedelta, datetime

from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_bot.handlers.cron_lesson_reminder import CronLessonReminder
from voice_bot.telegram_bot.handlers.cron_spreadsheet_sync import CronSpreadsheetSync


@dataclass
class CronJob:
    handler: type[BaseScheduleHandler]
    interval: timedelta = timedelta.max
    first: datetime = datetime.min
    last: datetime = datetime.max


CRON_JOBS: dict[str, CronJob] = {
    "lesson_reminder": CronJob(
        handler=CronLessonReminder,
        interval=timedelta(minutes=15),
        first=datetime(2023, 1, 1, 0, 0)
    ),
    "spreadsheet_sync": CronJob(
        handler=CronSpreadsheetSync,
        interval=timedelta(hours=1),
        first=datetime.utcnow() + timedelta(seconds=10)
    )
}
