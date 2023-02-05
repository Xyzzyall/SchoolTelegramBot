from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.user_authorization_service import UserAuthorizationService
from voice_bot.spreadsheets.models.user import User
from voice_bot.telegram_bot.base_claim import BaseClaim
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class AuthorizedUser(BaseClaim):
    @inject
    def __init__(self, auth_service: UserAuthorizationService, msg_builder: MessageBuilder):
        self._msg_builder = msg_builder
        self._auth_service = auth_service

    _user: User | None = None

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        user = await self._auth_service.try_authorize(update.effective_user.username)
        if user:
            self._msg_builder.push_user(user)
            self._user = user
        return bool(user)

    def get_authorized_user(self) -> User | None:
        if not self._user:
            return None
        return self._user

    async def on_fail(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Команда недоступна для неизвестных пользователей")
