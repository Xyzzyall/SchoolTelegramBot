import functools
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import TypeVar


@dataclass
class _CacheEntry:
    value: any
    creation_date: datetime
    duration: timedelta


class SimpleCache:
    T = TypeVar('T', bound=callable)

    def __init__(self):
        self._cache = dict[str, _CacheEntry]()

    def cache_decorator(self, key_format_str: str, lifespan: timedelta):
        def decorator(func: SimpleCache.T) -> SimpleCache.T:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                key = key_format_str.format(*args, **kwargs)
                if key in self._cache:
                    val = self._cache[key]
                    if val.creation_date + val.duration >= datetime.now():
                        return val.value
                new_val = await func(*args, **kwargs)
                self._cache[key] = _CacheEntry(new_val, datetime.now(), lifespan)
                return new_val
            return wrapper
        return decorator

    def delete_key(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()


_c = SimpleCache()
delete_key = _c.delete_key
clear_cache = _c.clear
simplecache = _c.cache_decorator
