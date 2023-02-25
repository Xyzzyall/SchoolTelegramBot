from injector import singleton, inject

from voice_bot.domain.claims.role_claim import RoleClaim
from voice_bot.misc import simple_cache
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.spreadsheets.users_table import UsersTableService


@singleton
class CacheService:
    @inject
    def __init__(self, users: UsersTableService, params: ParamsTableService):
        self._params = params
        self._users = users

    def clear_users_cache(self):
        self._users.delete_cache()

    def clear_settings_cache(self):
        self._params.delete_cache()

    def clear_claims_cache(self):
        RoleClaim.delete_cache()

    @staticmethod
    def clear_all_cache():
        simple_cache.clear_cache()

