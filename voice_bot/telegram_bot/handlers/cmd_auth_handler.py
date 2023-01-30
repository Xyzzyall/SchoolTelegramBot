import structlog
from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.user_authorization import UserAuthorization
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdAuthHandler(BaseUpdateHandler):
    @inject
    def __init__(self, user_auth: UserAuthorization, msg_builder: MessageBuilder):
        self._msg_builder = msg_builder
        self._user_auth = user_auth
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self._user_auth.register_user(update.message.from_user.username, ' '.join(context.args))
        if user:
            await self._logger.ainfo("User successfully authorized", user_id=user.unique_id,
                                     new_tg_login=user.telegram_login)
            self._msg_builder.push('ученик_фио', user.fullname)
            template = "Авторизация.Успешно"
        else:
            template = "Авторизация.Ошибка"

        await update.message.reply_text(await self._msg_builder.format(template))
