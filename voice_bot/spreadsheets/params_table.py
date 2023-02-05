from abc import ABC, abstractmethod

from injector import singleton

from voice_bot.spreadsheets.cached_table import _CachedTable


@singleton
class ParamsTableService(_CachedTable, ABC):
    @abstractmethod
    async def map_template(self, key: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def get_param(self, key: str) -> str:
        pass

    @abstractmethod
    async def rewrite_param(self, key: str, val: str):
        pass
