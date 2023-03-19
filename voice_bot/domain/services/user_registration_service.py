from injector import inject
from sqlalchemy import select

from voice_bot.db.enums import YesNo
from voice_bot.db.models import User
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.roles import UserRoles
from voice_bot.domain.services.cache_service import CacheService
from voice_bot.domain.services.reminders_service import RemindersService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class UserRegistrationService:
    @inject
    def __init__(self,
                 params: ParamsTableService,
                 users: UsersService,
                 session: UpdateSession,
                 cache: CacheService,
                 reminders: RemindersService):
        self._reminders = reminders
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

        user: User = users[0]
        user.telegram_login = telegram_login
        user.telegram_chat_id = chat_id

        await self._users.send_text_message_to_roles(
            f"Ученик {users[0].fullname} зарегистрировался в боте!",
            set(UserRoles.sysadmin), send_as_is=True
        )

        await self._session.commit()

        # по-умолчанию всем ставлю напоминалку за сутки
        if user.is_admin == YesNo.NO:
            await self._reminders.set_reminder_state_for(user, "за сутки", True)

        self._cache.clear_claims_cache()

        return users[0]
