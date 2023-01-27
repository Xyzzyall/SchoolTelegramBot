from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.user_authorization import UserAuthorization
from voice_bot.telegram_bot.base_claim import BaseClaim
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class AuthorizedUser(BaseClaim):
    @inject
    def __init__(self, auth_service: UserAuthorization):
        self._auth_service = auth_service

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        return bool(await self._auth_service.try_authorize(update.message.from_user.username))

    async def on_fail(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Команда недоступна для неизвестных пользователей")
