import uuid
from datetime import datetime, timedelta

from injector import singleton

from voice_bot.telegram_bot.navigation.base_classes import NavigationContext


@singleton
class CallbackDataCodec:
    def __init__(self):
        self._cache = dict[str, NavigationContext]()
        self._reverse_cache = dict[NavigationContext, str]()
        self._timestamps = dict[str, datetime]()

    @staticmethod
    def _generate_key():
        return str(uuid.uuid4())

    def encode(self, nav_context: NavigationContext) -> str:
        if nav_context in self._reverse_cache:
            return self._reverse_cache[nav_context]
        key = self._generate_key()
        self._timestamps[key] = datetime.now()
        self._cache[key] = nav_context
        self._reverse_cache[nav_context] = key
        return key

    def decode(self, s: str) -> NavigationContext | None:
        if s not in self._cache:
            return None
        return self._cache[s]

    def clear_old(self):
        for key in self._cache:
            if self._timestamps[key] - datetime.now() > timedelta(hours=24):
                entry = self._cache[key]
                self._cache.pop(key)
                self._reverse_cache.pop(entry)
                self._timestamps.pop(key)
