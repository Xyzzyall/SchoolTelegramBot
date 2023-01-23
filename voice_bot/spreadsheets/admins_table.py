from abc import ABC, abstractmethod

from injector import singleton

from voice_bot.spreadsheets.cached_table import CachedTable
from voice_bot.spreadsheets.models.admin import Admin


@singleton
class AdminsTable(CachedTable, ABC):
    @abstractmethod
    async def get_admin(self, telegram_login: str) -> Admin:
        pass

