import os

from injector import singleton, inject, Injector

from voice_bot.spreadsheets.google_cloud.google_params_table import GoogleParamsTable
from voice_bot.spreadsheets.google_cloud.google_schedule_table import GoogleScheduleTable
from voice_bot.spreadsheets.google_cloud.google_users_table import GoogleUsersTable
from voice_bot.spreadsheets.params_table import ParamsTable
from voice_bot.spreadsheets.schedule_table import ScheduleTable
from voice_bot.spreadsheets.users_table import UsersTable


@singleton
class VoiceBotConfigurator:
    @inject
    def __init__(self, injector: Injector):
        self.telegram_bot_token = os.environ.get("VOICE_BOT_TELEGRAM_TOKEN")
        self._injector = injector

        self._injector_bind_google_sheets()

    def _injector_bind_google_sheets(self):
        self._injector.binder.bind(ParamsTable, GoogleParamsTable)
        self._injector.binder.bind(UsersTable, GoogleUsersTable)
        self._injector.binder.bind(ScheduleTable, GoogleScheduleTable)
