from abc import abstractmethod
from typing import TypeVar, Generic

_Model = TypeVar('_Model')


class _DumpedTable(Generic[_Model]):
    @abstractmethod
    async def dump_records(self, **kwargs) -> list[_Model]:
        pass

    @abstractmethod
    async def rewrite_all_records(self, records: list[_Model]):
        pass
