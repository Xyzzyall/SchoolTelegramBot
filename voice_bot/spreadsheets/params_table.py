from abc import ABC, abstractmethod

from injector import singleton

from voice_bot.spreadsheets.cached_table import CachedTable


@singleton
class ParamsTable(CachedTable, ABC):
    @abstractmethod
    async def map_template(self, key: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def get_param(self, key: str) -> str:
        pass
