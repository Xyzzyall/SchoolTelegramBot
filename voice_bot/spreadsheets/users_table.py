from abc import ABC, abstractmethod
from typing import Callable

from injector import singleton

from voice_bot.spreadsheets.cached_table import _CachedTable
from voice_bot.spreadsheets.models.user import User


@singleton
class UsersTableService(_CachedTable, ABC):
    @abstractmethod
    async def get_user(self, filter_lambda: Callable[[User], bool]) -> User:
        pass

    @abstractmethod
    async def get_users(self) -> list[User]:
        pass

    @abstractmethod
    async def rewrite_user(self, user: User):
        pass
