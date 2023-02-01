from injector import inject

from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.users_table import UsersTable
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class Users:
    @inject
    def __init__(self, users_table: UsersTable):
        self._users_table = users_table

    async def get_user_by_id(self, unique_id: str) -> User | None:
        return await self._users_table.get_user(lambda u: u.unique_id == unique_id)
