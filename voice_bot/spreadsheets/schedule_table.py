from abc import ABC, abstractmethod
from datetime import datetime

from injector import singleton


@singleton
class ScheduleTable(ABC):
    @abstractmethod
    async def get_schedule_for_time(self, time: datetime):
        pass
