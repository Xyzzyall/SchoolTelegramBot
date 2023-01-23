from datetime import timedelta

from injector import inject

from voice_bot.spreadsheets.misc import simple_cache
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.users_table import UsersTable


class GoogleUsersTable(UsersTable):
    @inject
    def __init__(self):
        pass

    _TABLE_CACHE_KEY = "google_users"

    def delete_cache(self):
        simple_cache.delete_key(self._TABLE_CACHE_KEY)

    @simplecache(_TABLE_CACHE_KEY, timedelta(days=365))
    def _fetch_users_table(self) -> dict[str, User]:
        pass

    async def get_user(self, telegram_login: str) -> User:
        pass

    async def authorize_user(self, telegram_login: str, secret_word: str) -> bool:
        pass

