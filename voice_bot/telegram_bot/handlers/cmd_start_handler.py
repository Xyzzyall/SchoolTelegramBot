from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.telegram_bot.base_handler import BaseHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdStartHandler(BaseHandler):
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"i'm gay {self}!")
