import structlog
from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.spreadsheets.params_table import ParamsTable
from voice_bot.spreadsheets.users_table import UsersTable
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdAuthHandler(BaseUpdateHandler):
    @inject
    def __init__(self, params: ParamsTable, users: UsersTable):
        self._users = users
        self._params = params
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        auth_res, user = await self._users.authorize_user(update.message.from_user.username, ' '.join(context.args))
        if auth_res:
            await self._logger.ainfo("User successfully authorized", user_id=user.unique_id, new_tg_login=user.telegram_login)
            template = await self._params.map_template("Авторизация.Успешно", **{'ученик_фио': user.fullname})
        else:
            template = await self._params.map_template("Авторизация.Ошибка")

        await update.message.reply_text(template)
