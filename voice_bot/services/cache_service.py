from injector import singleton, inject

from voice_bot.spreadsheets.misc import simple_cache
from voice_bot.spreadsheets.params_table import ParamsTable
from voice_bot.spreadsheets.users_table import UsersTable


@singleton
class CacheService:
    @inject
    def __init__(self, users: UsersTable, params: ParamsTable):
        self._params = params
        self._users = users

    def clear_users_cache(self):
        self._users.delete_cache()

    def clear_settings_cache(self):
        self._params.delete_cache()

    @staticmethod
    def clear_all_cache():
        simple_cache.clear_cache()

