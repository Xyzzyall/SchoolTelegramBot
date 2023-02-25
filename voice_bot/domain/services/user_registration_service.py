from injector import inject
from sqlalchemy import select

from voice_bot.db.models import User
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.roles import UserRoles
from voice_bot.domain.services.cache_service import CacheService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.telegram_di_scope import telegramupdate


# todo rename this class to UserRegistration and move authorization logic to claims
@telegramupdate
class UserRegistrationService:
    @inject
    def __init__(self, params: ParamsTableService, users: UsersService, session: UpdateSession, cache: CacheService):
        self._session = session.session
        self._params = params
        self._users = users
        self._cache = cache

    async def register_user(self, telegram_login: str, chat_id: str, secret_code: str) -> User | None:
        if not secret_code:
            return None

        query = select(User).where(User.secret_code == secret_code)
        users = (await self._session.scalars(query)).all()

        if len(users) > 1:
            msg = f"Кодовое слово '{secret_code}' задублировано у пользователей" \
                  f" {', '.join((user.unique_name for user in users))}. Нужно исправить и провести синхронизацию."
            await self._users.send_text_message_to_roles(msg, set(UserRoles.sysadmin), send_as_is=True)
            return None

        if not users:
            return None

        users[0].telegram_login = telegram_login
        users[0].telegram_chat_id = chat_id

        await self._users.send_text_message_to_roles(
            f"Ученик {users[0].fullname} зарегистрировался в боте!",
            set(UserRoles.sysadmin), send_as_is=True
        )

        await self._session.commit()

        self._cache.clear_claims_cache()

        return users[0]
