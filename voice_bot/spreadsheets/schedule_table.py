from abc import ABC, abstractmethod
from datetime import date, timedelta

from injector import singleton

from voice_bot.spreadsheets.dumped_table import _DumpedTable
from voice_bot.spreadsheets.models.spreadsheet_schedule_record import SpreadsheetScheduleRecord


@singleton
class ScheduleTableService(_DumpedTable[SpreadsheetScheduleRecord], ABC):
    @abstractmethod
    async def get_schedule_for_timespan(
            self, day_start: date, day_end: date) -> dict[str, list[SpreadsheetScheduleRecord]]:
        pass

    @abstractmethod
    async def get_standard_schedule(self) -> dict[str, list[SpreadsheetScheduleRecord]]:
        pass

    @abstractmethod
    async def create_schedule_sheet_for_week(self, monday: date):
        pass

    @abstractmethod
    async def get_all_schedule_sheet_mondays(self, weeks_back: int, weeks_forward: int) -> set[date]:
        pass

    STANDARD_SCHEDULE_TABLE_NAME = "Стандарт"

    @staticmethod
    def generate_table_name(monday: date) -> str:
        return f"{monday.strftime('%d.%m')}-{(monday + timedelta(days=6)).strftime('%d.%m')}"
