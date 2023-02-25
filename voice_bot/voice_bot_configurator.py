import json
import os
from pathlib import Path

from injector import singleton, inject, Injector

from voice_bot.spreadsheets.admins_table import AdminsTableService
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.spreadsheets.schedule_table import ScheduleTableService
from voice_bot.spreadsheets.users_table import UsersTableService


@singleton
class VoiceBotConfigurator:
    @inject
    def __init__(self, injector: Injector):
        configs_path = Path(os.getenv("VOICE_BOT_CONFIGS_JSON_PATH"))
        if not configs_path:
            raise RuntimeError("Cannot get config file path from env key VOICE_BOT_CONFIGS_JSON_PATH")

        self._injector = injector

        with open(configs_path) as file:
            configs = json.load(file)

            self.telegram_bot_token = configs["telegram_token"]

            self.db_connection_str = configs["db_conn_str"]

            self._injector_bind_google_sheets()
            self.google_token_path = configs_path.parent / configs["google"]["token_path"]
            self.google_settings_table_link = configs["google"]["table_settings_link"]
            self.google_schedule_table_link = configs["google"]["table_schedule_link"]

    def _injector_bind_google_sheets(self):
        from voice_bot.spreadsheets.google_cloud.google_params_table import GoogleParamsTableService
        self._injector.binder.bind(ParamsTableService, GoogleParamsTableService)
        from voice_bot.spreadsheets.google_cloud.google_users_table import GoogleUsersTableService
        self._injector.binder.bind(UsersTableService, GoogleUsersTableService)
        from voice_bot.spreadsheets.google_cloud.google_schedule_table import GoogleScheduleTableService
        self._injector.binder.bind(ScheduleTableService, GoogleScheduleTableService)
        from voice_bot.spreadsheets.google_cloud.google_admins_table import GoogleAdminsTableService
        self._injector.binder.bind(AdminsTableService, GoogleAdminsTableService)
