from datetime import timedelta

from voice_bot.spreadsheets.google_cloud.gspread import gs_sheet
from voice_bot.spreadsheets.misc import simple_cache
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.params_table import ParamsTable


class GoogleParamsTable(ParamsTable):
    _TABLE_CACHE_KEY = "google_params"

    def delete_cache(self):
        simple_cache.delete_key(self._TABLE_CACHE_KEY)

    @simplecache(_TABLE_CACHE_KEY, timedelta(days=365))
    async def _get_params_table_and_parse(self) -> (dict[str, str], dict[str, str]):
        cells = gs_sheet.worksheet("Настройки").get_values()
        templates, params = dict[str, str](), dict[str, str]()
        for row in cells[2:]:
            if row[0] != '':
                templates[row[0]] = row[1]
            if row[3] != '':
                params[row[3]] = row[4]
        return params, templates

    async def _get_templates(self) -> dict[str, str]:
        _, templates = await self._get_params_table_and_parse()
        return templates

    async def _get_params(self) -> dict[str, str]:
        params, _ = await self._get_params_table_and_parse()
        return params

    async def map_template(self, key: str, **kwargs) -> str:
        templates = await self._get_templates()
        if key not in templates:
            raise KeyError("Message template is not found")
        return templates[key].format(**kwargs, **(await self._get_params()))

    async def get_param(self, key: str) -> str:
        params = await self._get_params()
        if key not in params:
            raise KeyError("Parameter is not found")
        return params[key]
