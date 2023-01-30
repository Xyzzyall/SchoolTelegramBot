from datetime import timedelta

from injector import inject

from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.spreadsheets.misc import simple_cache
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.params_table import ParamsTable


class GoogleParamsTable(ParamsTable):
    @inject
    def __init__(self, gspread: GspreadClient):
        self._gspread = gspread

    _SETTINGS_TABLE_CACHE_KEY = "google_params_settings"
    _TEMPLATES_TABLE_CACHE_KEY = "google_params_templates"

    def delete_cache(self):
        simple_cache.delete_key(self._SETTINGS_TABLE_CACHE_KEY)
        simple_cache.delete_key(self._TEMPLATES_TABLE_CACHE_KEY)

    @simplecache(_TEMPLATES_TABLE_CACHE_KEY, timedelta(days=365))
    async def _get_templates(self) -> dict[str, str]:
        templates = dict[str, str]()
        cells = self._gspread.gs_settings_sheet.worksheet("Шаблоны сообщений").get_values()
        for row in cells[1:]:
            if not row[0]:
                continue
            templates[row[0]] = row[1]
        return templates

    @simplecache(_SETTINGS_TABLE_CACHE_KEY, timedelta(days=365))
    async def _get_params(self) -> dict[str, str]:
        params = dict[str, str]()
        cells = self._gspread.gs_settings_sheet.worksheet("Настройки").get_values()
        for row in cells[1:]:
            if not row[0]:
                continue
            params[row[0]] = row[1]
        return params

    async def map_template(self, key: str, **kwargs) -> str:
        templates = await self._get_templates()
        if key not in templates:
            raise KeyError("Message template is not found")
        params = await self._get_params()
        return templates[key].format(**kwargs, **params)

    async def get_param(self, key: str) -> str:
        params = await self._get_params()
        if key not in params:
            raise KeyError("Parameter is not found")
        return params[key]
