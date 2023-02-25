from abc import abstractmethod, ABC


class Cached(ABC):
    @staticmethod
    @abstractmethod
    def delete_cache():
        pass
