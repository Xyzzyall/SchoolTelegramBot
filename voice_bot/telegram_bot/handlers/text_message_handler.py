import structlog
from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.domain.roles import UserRoles
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.spreadsheet_sync_service import SpreadsheetSyncService
from voice_bot.domain.services.user_registration_service import UserRegistrationService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.domain.utils.user_utils import user_has_role
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class TextMessageHandler(BaseUpdateHandler):
    @inject
    def __init__(self,
                 users: UsersService,
                 msg_builder: MessageBuilder,
                 user_reg: UserRegistrationService,
                 spreadsheet_sync: SpreadsheetSyncService):
        self._users = users
        self._spreadsheet_sync = spreadsheet_sync
        self._user_reg = user_reg
        self._msg_builder = msg_builder
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self._users.get_user_with_roles_by_tg_login(update.effective_user.username)

        if user:
            if user_has_role(user, UserRoles.student):
                await update.effective_message.reply_text(
                    await self._msg_builder.format("Любое_сообщение")
                )
                return

            if user_has_role(user, UserRoles.sysadmin):
                await update.effective_message.reply_text(f"Что?\n{update.effective_message.text}?")
                return
            return

        user = await self._user_reg.register_user(
            update.effective_user.username,
            str(update.effective_message.chat_id),
            update.effective_message.text
        )

        if user:
            await self._logger.info("SpreadsheetUser successfully authorized", user_id=user.unique_name,
                                     new_tg_login=user.telegram_login)
            self._msg_builder.push('ученик_фио', user.fullname)
            template = "Авторизация.Успешно"
        else:
            template = "Авторизация.Ошибка"

        await update.effective_message.reply_text(await self._msg_builder.format(template))


