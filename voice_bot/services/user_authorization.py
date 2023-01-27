from injector import inject

from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.params_table import ParamsTable
from voice_bot.spreadsheets.users_table import UsersTable
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class UserAuthorization:
    @inject
    def __init__(self, users: UsersTable, params: ParamsTable):
        self._params = params
        self._users = users

    async def register_user(self, telegram_login: str, secret_code: str) -> User | None:
        if not secret_code:
            return None

        user = await self._users.get_user(lambda v: v.secret_code == secret_code)
        if not user:
            return None

        user.secret_code = ''
        user.telegram_login = telegram_login
        await self._users.rewrite_user(user)
        return user

    async def try_authorize(self, telegram_login: str) -> User | None:
        return await self._users.get_user(lambda v: v.telegram_login == telegram_login)

    async def try_authorize_admin(self, telegram_login: str) -> bool:
        return (await self._params.get_param("логин_преподавателя")).lower() == telegram_login.lower()
