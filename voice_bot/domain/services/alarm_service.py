import structlog
from injector import inject

from voice_bot.domain.roles import UserRoles
from voice_bot.domain.services.users_service import UsersService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class AlarmService:
    @inject
    def __init__(self, users: UsersService):
        self._users = users
        self._logger = structlog.get_logger()

    async def warning(self, text: str, src: type, **kwargs):
        await self._logger.warning(text, class_name=src, **kwargs)
        await self._users.send_text_message_to_roles(
            "*Ой, что-то пошло не так* 😣 \n" +
            f"{text}\n" +
            f"Параметры: {', '.join(f'{key}={val}' for key, val in kwargs.items())}",
            roles={UserRoles.sysadmin},
            send_as_is=True
        )

    async def error(self, text: str, src: type, **kwargs):
        await self._logger.error(str, class_name=src, **kwargs)
        await self._users.send_text_message_to_roles(
            f"""*Хьюстон, у нас проблемы. Произошла серьёзная ошибка* 💩
            {text}
            Параметры: {', '.join(f'{key}={val}' for key, val in kwargs.items())}""",
            roles={UserRoles.sysadmin},
            send_as_is=True
        )
