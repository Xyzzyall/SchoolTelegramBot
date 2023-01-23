from datetime import timedelta

from voice_bot.spreadsheets.misc import simple_cache
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.params_table import ParamsTable


class GoogleParamsTable(ParamsTable):
    _TABLE_CACHE_KEY = "google_params"

    def delete_cache(self):
        simple_cache.delete_key(self._TABLE_CACHE_KEY)

    @simplecache(_TABLE_CACHE_KEY, timedelta(days=365))
    def _get_params_table_and_parse(self) -> (dict[str, str], dict[str, str]):
        pass

    def _get_templates(self) -> dict[str, str]:
        _, templates = self._get_params_table_and_parse()
        return templates

    def _get_params(self) -> dict[str, str]:
        params, _ = self._get_params_table_and_parse()
        return params

    async def map_template(self, key: str, **kwargs) -> str:
        templates = self._get_templates()
        if key not in templates:
            raise KeyError("Message template is not found")
        return templates[key].format(**kwargs)

    async def get_param(self, key: str) -> str:
        params = self._get_params()
        if key not in params:
            raise KeyError("Parameter is not found")
        return params[key]
