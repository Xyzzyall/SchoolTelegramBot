from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.services.user_authorization_service import UserAuthorizationService
from voice_bot.telegram_bot.base_claim import BaseClaim
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class AdminUser(BaseClaim):
    @inject
    def __init__(self, user_auth: UserAuthorizationService):
        self._user_auth = user_auth

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        return await self._user_auth.try_authorize_admin(update.effective_user.username)

    async def on_fail(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Команда доступна только администраторам")
