from abc import ABC, abstractmethod
from datetime import datetime

from injector import singleton

from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord


@singleton
class ScheduleTable(ABC):
    @abstractmethod
    async def get_schedule_for_timespan(
            self, day_start: datetime, day_end: datetime) -> dict[str, list[ScheduleRecord]]:
        pass

    @abstractmethod
    async def get_standard_schedule(self) -> dict[str, list[ScheduleRecord]]:
        pass

    @abstractmethod
    async def create_schedule_sheet_for_week(self, monday: datetime):
        pass

    @abstractmethod
    async def get_all_schedule_sheets(self) -> list[str]:
        pass
