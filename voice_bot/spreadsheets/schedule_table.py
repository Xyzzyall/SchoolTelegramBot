from abc import ABC, abstractmethod
from datetime import date

from injector import singleton

from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord


@singleton
class ScheduleTableService(ABC):
    @abstractmethod
    async def get_schedule_for_timespan(
            self, day_start: date, day_end: date) -> dict[str, list[ScheduleRecord]]:
        pass

    @abstractmethod
    async def get_standard_schedule(self) -> dict[str, list[ScheduleRecord]]:
        pass

    @abstractmethod
    async def create_schedule_sheet_for_week(self, monday: date):
        pass

    @abstractmethod
    async def get_all_schedule_sheet_mondays(self, weeks_back: int, weeks_forward: int) -> set[date]:
        pass
