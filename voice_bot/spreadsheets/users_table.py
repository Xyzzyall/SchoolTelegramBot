from abc import ABC, abstractmethod
from typing import Callable

from injector import singleton

from voice_bot.misc.cached import Cached
from voice_bot.spreadsheets.dumped_table import _DumpedTable
from voice_bot.spreadsheets.models.spreadsheet_user import SpreadsheetUser


@singleton
class UsersTableService(_DumpedTable[SpreadsheetUser], Cached, ABC):
    @abstractmethod
    async def get_user(self, filter_lambda: Callable[[SpreadsheetUser], bool]) -> SpreadsheetUser:
        pass

    @abstractmethod
    async def get_users(self) -> list[SpreadsheetUser]:
        pass

    @abstractmethod
    async def rewrite_user(self, user: SpreadsheetUser):
        pass