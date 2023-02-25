from abc import ABC, abstractmethod

from injector import singleton

from voice_bot.misc.cached import Cached
from voice_bot.spreadsheets.dumped_table import _DumpedTable
from voice_bot.spreadsheets.models.spreadsheet_admin import SpreadsheetAdmin


@singleton
class AdminsTableService(_DumpedTable[SpreadsheetAdmin], Cached, ABC):
    @abstractmethod
    async def get_admin(self, telegram_login: str) -> SpreadsheetAdmin:
        pass

