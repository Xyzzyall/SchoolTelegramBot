from injector import inject

from voice_bot.services.admins_service import AdminsService
from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.spreadsheets.users_table import UsersTableService
from voice_bot.telegram_di_scope import telegramupdate


# todo rename this class to UserRegistration and move authorization logic to claims
@telegramupdate
class UserAuthorizationService:
    @inject
    def __init__(self, users: UsersTableService, params: ParamsTableService, admins: AdminsService):
        self._admins = admins
        self._params = params
        self._users = users

    async def register_user(self, telegram_login: str, chat_id: str, secret_code: str) -> User | None:
        if not secret_code:
            return None

        user = await self._users.get_user(lambda v: v.secret_code == secret_code)
        if not user:
            return None

        user.secret_code = ''
        user.telegram_login = telegram_login
        user.chat_id = chat_id
        await self._users.rewrite_user(user)

        await self._admins.send_message_to_admin(f"Ученик {user.fullname} зарегистрировался в боте!")

        return user

    async def try_authorize(self, telegram_login: str) -> User | None:
        return await self._users.get_user(lambda v: v.telegram_login == telegram_login)

    async def try_authorize_admin(self, telegram_login: str) -> bool:
        return (await self._params.get_param("логин_преподавателя")).lower() == telegram_login.lower()
