from injector import inject

from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.users_table import UsersTableService
from voice_bot.telegram_bot.telegram_bot_proxy import TelegramBotProxy
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class UsersService:
    @inject
    def __init__(self, users_table: UsersTableService, tg_bot_proxy: TelegramBotProxy):
        self._tg_bot_proxy = tg_bot_proxy
        self._users_table = users_table

    async def get_user_by_id(self, unique_id: str) -> User | None:
        return await self._users_table.get_user(lambda u: u.unique_id == unique_id)

    async def send_message(self, user: User, text: str):
        if not user.chat_id:
            raise RuntimeError(f"Cannot send message to user unique_id={user.unique_id} without chat_id")

        await self._tg_bot_proxy.bot.send_message(user.chat_id, text, parse_mode='Markdown')

    async def get_authorized_users(self) -> list[User]:
        return list(
            filter(lambda x: bool(x.telegram_login), await self._users_table.get_users())
        )
