import json
import uuid

from injector import singleton

from voice_bot.telegram_bot.navigation.base_classes import NavigationContext


@singleton
class CallbackDataCodec:
    def __init__(self):
        self._cache = dict[str, str]()
        self._reverse_cache = dict[str, str]()

    @staticmethod
    def _generate_key():
        return str(uuid.uuid4())

    def encode(self, nav_context: NavigationContext) -> str:
        str_nav_context = self._str_data(nav_context)
        if str_nav_context in self._reverse_cache:
            return self._reverse_cache[str_nav_context]
        key = self._generate_key()
        self._cache[key] = str_nav_context
        self._reverse_cache[str_nav_context] = key
        return key

    def decode(self, s: str) -> NavigationContext | None:
        if s not in self._cache:
            return None
        return self._parse_data(self._cache[s])

    @staticmethod
    def _parse_data(data: str) -> NavigationContext:
        got_data = json.loads(data)
        return NavigationContext(
            root_cmd=got_data["c"],
            tree_path=got_data["p"].split('.'),
            context_vars={},
            kwargs=got_data["v"]
        )

    @staticmethod
    def _str_data(nav_context: NavigationContext) -> str:
        res = json.dumps({
            "c": nav_context.root_cmd,
            "p": '.'.join(nav_context.tree_path),
            "v": nav_context.kwargs
        })
        return res
