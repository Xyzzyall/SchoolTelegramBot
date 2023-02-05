import os

from injector import singleton, inject, Injector

from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.spreadsheets.schedule_table import ScheduleTableService
from voice_bot.spreadsheets.users_table import UsersTableService


@singleton
class VoiceBotConfigurator:
    @inject
    def __init__(self, injector: Injector):
        self.telegram_bot_token = os.environ.get("VOICE_BOT_TELEGRAM_TOKEN")
        self._injector = injector

        self._injector_bind_google_sheets()
        self.google_settings_table_link = "https://docs.google.com/spreadsheets/d/1ubHM5ZbwXa9xDUDB_JSYJHM9BX7T_fMY0QM9Cx2ZEek/edit?usp=sharing"
        self.google_schedule_table_link = "https://docs.google.com/spreadsheets/d/1pb3MtvVFXNtqHnsnR9Eqm6ACgVxieDx-Gx-JixEydDA/edit?usp=sharing"

    def _injector_bind_google_sheets(self):
        from voice_bot.spreadsheets.google_cloud.google_params_table import GoogleParamsTableService
        self._injector.binder.bind(ParamsTableService, GoogleParamsTableService)
        from voice_bot.spreadsheets.google_cloud.google_users_table import GoogleUsersTableService
        self._injector.binder.bind(UsersTableService, GoogleUsersTableService)
        from voice_bot.spreadsheets.google_cloud.google_schedule_table import GoogleScheduleTableService
        self._injector.binder.bind(ScheduleTableService, GoogleScheduleTableService)

