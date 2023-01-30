import gspread
from injector import singleton, inject

from voice_bot.voice_bot_configurator import VoiceBotConfigurator


@singleton
class GspreadClient:
    @inject
    def __init__(self, conf: VoiceBotConfigurator):
        gs = gspread.service_account()
        self.gs_settings_sheet = gs.open_by_url(conf.google_settings_table_link)
        self.gs_schedule_sheet = gs.open_by_url(conf.google_schedule_table_link)

