import functools
import json
from dataclasses import dataclass
from datetime import timedelta, datetime
from hashlib import md5
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

    def cache_decorator(self, key_prefix: str, lifespan: timedelta):
        def decorator(func: SimpleCache.T) -> SimpleCache.T:
            @functools.wraps(func)
            async def wrapper(other_self, *args, **kwargs):
                args_dumped = json.dumps(args, default=str) + json.dumps(kwargs, default=str)

                key_hash = md5(args_dumped.encode("utf-8")).hexdigest()
                key = f"{key_prefix}:{key_hash}"
                if key in self._cache:
                    val = self._cache[key]

                    if val.creation_date + val.duration >= datetime.now():
                        return val.value

                new_val = await func(other_self, *args, **kwargs)
                self._cache[key] = _CacheEntry(new_val, datetime.now(), lifespan)
                return new_val
            return wrapper
        return decorator

    def delete_key(self, key: str):
        for cache_key in self._cache:
            if cache_key.startswith(key):
                self._cache.pop(cache_key, None)
                return

    def clear(self):
        self._cache.clear()


_c = SimpleCache()
delete_key = _c.delete_key
clear_cache = _c.clear
simplecache = _c.cache_decorator
