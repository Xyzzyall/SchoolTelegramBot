import structlog
from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.spreadsheets.params_table import ParamsTable
from voice_bot.telegram_bot.base_handler import BaseHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdStartHandler(BaseHandler):
    @inject
    def __init__(self, params: ParamsTable):
        self._params = params
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._logger.ainfo("cringe!")
        await update.message.reply_text(f"i'm gay {self}!")
