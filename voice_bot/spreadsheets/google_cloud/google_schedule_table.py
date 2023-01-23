from datetime import datetime, timedelta

from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.spreadsheets.schedule_table import ScheduleTable


class GoogleScheduleTable(ScheduleTable):

    @simplecache("google_schedule_{}", timedelta(minutes=10))
    def _get_schedule_from_table(self, table_name: str) -> dict[str, ScheduleRecord]:
        pass

    async def get_schedule_for_time(self, time: datetime):
        pass

