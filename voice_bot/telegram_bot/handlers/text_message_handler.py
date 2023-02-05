import structlog
from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.user_authorization_service import UserAuthorizationService
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.claims.admin_user import AdminUser
from voice_bot.telegram_bot.claims.authorized_user import AuthorizedUser
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class TextMessageHandler(BaseUpdateHandler):
    @inject
    def __init__(self,
                 auth_user_claim: AuthorizedUser,
                 admin_user_claim: AdminUser,
                 msg_builder: MessageBuilder,
                 user_auth: UserAuthorizationService):
        self._admin_user_claim = admin_user_claim
        self._user_auth = user_auth
        self._msg_builder = msg_builder
        self._auth_user_claim = auth_user_claim
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if await self._auth_user_claim.handle(update, context):
            await update.effective_message.reply_text(
                await self._msg_builder.format("Любое_сообщение")
            )
            return
        if await self._admin_user_claim.handle(update, context):
            await update.effective_message.reply_text(f"Что?\n{update.effective_message.text}?")
            return

        user = await self._user_auth.register_user(
            update.effective_user.username,
            str(update.effective_message.chat_id),
            update.effective_message.text
        )

        if user:
            await self._logger.ainfo("User successfully authorized", user_id=user.unique_id,
                                     new_tg_login=user.telegram_login)
            self._msg_builder.push('ученик_фио', user.fullname)
            template = "Авторизация.Успешно"
        else:
            template = "Авторизация.Ошибка"

        await update.effective_message.reply_text(await self._msg_builder.format(template))


