from abc import abstractmethod, ABC


class CachedTable(ABC):
    @abstractmethod
    def delete_cache(self):
        pass
