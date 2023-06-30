from datetime import timedelta

from injector import inject

from voice_bot.misc import simple_cache
from voice_bot.misc.simple_cache import simplecache
from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.spreadsheets.params_table import ParamsTableService


class GoogleParamsTableService(ParamsTableService):
    @inject
    def __init__(self, gspread: GspreadClient):
        self._gspread = gspread

    _SETTINGS_TABLE_CACHE_KEY = "google_params_settings"

    _TEMPLATES_TABLE_CACHE_KEY = "google_params_templates"

    @staticmethod
    def delete_cache():
        simple_cache.delete_key(GoogleParamsTableService._SETTINGS_TABLE_CACHE_KEY)
        simple_cache.delete_key(GoogleParamsTableService._TEMPLATES_TABLE_CACHE_KEY)

    @simplecache(_TEMPLATES_TABLE_CACHE_KEY, timedelta(days=365))
    async def _get_templates(self) -> dict[str, str]:
        templates = dict[str, str]()

        worksheet = await self._gspread.get_settings_worksheet("Шаблоны сообщений")

        cells = worksheet.get_values()
        for row in cells[1:]:
            if not row[0]:
                continue

            templates[row[0]] = row[1]

        return templates

    @simplecache(_SETTINGS_TABLE_CACHE_KEY, timedelta(days=365))
    async def _get_params(self) -> dict[str, str]:
        params = dict[str, str]()

        worksheet = await self._gspread.get_settings_worksheet("Настройки")

        cells = worksheet.get_values()

        for row in cells[1:]:
            if not row[0]:
                continue

            params[row[0]] = row[1]

        return params

    async def map_template(self, key: str, **kwargs) -> str:
        templates = await self._get_templates()

        if key not in templates:
            return key

        params = await self._get_params()

        return templates[key].format(**kwargs, **params)

    async def get_param(self, key: str) -> str:
        params = await self._get_params()

        if key not in params:
            raise KeyError(f"Parameter '{key}' is not found")

        return params[key]

    async def rewrite_param(self, key: str, val: str):
        worksheet = await self._gspread.get_settings_worksheet("Настройки")

        cells = worksheet.get_values()
        row_id = 0

        for i, row in enumerate(cells[1:]):
            if row[0] == key:
                row_id = i + 2

        if row_id == 0:
            raise KeyError(f"Parameter '{key}' is not found")

        worksheet.update(f'A{row_id}:B{row_id}', [[key, val]])

        simple_cache.delete_key(self._SETTINGS_TABLE_CACHE_KEY)

