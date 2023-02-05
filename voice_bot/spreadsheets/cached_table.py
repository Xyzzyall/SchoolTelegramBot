from abc import abstractmethod, ABC


class _CachedTable(ABC):
    @abstractmethod
    def delete_cache(self):
        pass
