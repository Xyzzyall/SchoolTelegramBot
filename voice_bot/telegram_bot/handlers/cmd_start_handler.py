from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.navigation.navigation import Navigation
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdStartHandler(BaseUpdateHandler):
    @inject
    def __init__(self, navigation: Navigation):
        self._navigation = navigation

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass
