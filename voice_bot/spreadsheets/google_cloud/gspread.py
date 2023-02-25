from datetime import timedelta

import gspread
from gspread import Worksheet
from injector import singleton, inject

from voice_bot.misc.simple_cache import simplecache
from voice_bot.voice_bot_configurator import VoiceBotConfigurator


@singleton
class GspreadClient:
    @inject
    def __init__(self, conf: VoiceBotConfigurator):
        gs = gspread.service_account(filename=conf.google_token_path)
        self.gs_settings_sheet = gs.open_by_url(conf.google_settings_table_link)
        self.gs_schedule_sheet = gs.open_by_url(conf.google_schedule_table_link)

    @simplecache("gspread_settings_worksheet", timedelta(days=365))
    async def get_settings_worksheet(self, name: str) -> Worksheet:
        return self.gs_settings_sheet.worksheet(name)

    @simplecache("gspread_schedule_worksheet", timedelta(days=365))
    async def get_schedule_worksheet(self, name: str) -> Worksheet:
        return self.gs_schedule_sheet.worksheet(name)

