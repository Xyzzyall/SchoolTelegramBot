from abc import ABC, abstractmethod

from injector import singleton

from voice_bot.spreadsheets.cached_table import CachedTable
from voice_bot.spreadsheets.models.user import User


@singleton
class UsersTable(CachedTable, ABC):
    @abstractmethod
    async def authorize_user(self, telegram_login: str, secret_word: str) -> bool:
        pass

    @abstractmethod
    async def get_user(self, telegram_login: str) -> User:
        pass

