from datetime import datetime, timedelta

from voice_bot.spreadsheets.google_cloud.gspread import gs_sheet
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.spreadsheets.schedule_table import ScheduleTable


class GoogleScheduleTable(ScheduleTable):

    async def get_standard_schedule(self) -> dict[str, ScheduleRecord]:
        pass

    @simplecache("google_schedule_{}", timedelta(minutes=10))
    def _get_schedule_from_table(self, table_name: str) -> dict[str, ScheduleRecord]:
        cells = gs_sheet.worksheet(table_name).get_all_cells()
        pass

    async def get_schedule_for_timespan(self, day_start: datetime, day_end: datetime) -> dict[str, ScheduleRecord]:
        pass

