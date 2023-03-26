from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.navigation.base_classes import NavigationTree
from voice_bot.telegram_bot.navigation.navigation import Navigation
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class NavigationCommandHandler(BaseUpdateHandler):
    @inject
    def __init__(self, navigation: Navigation):
        self._navigation = navigation
        self._navigation_tree: NavigationTree = None

    def push_nav_tree(self, navigation_tree: NavigationTree):
        self._navigation_tree = navigation_tree

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        showed = await self._navigation.process_command(
            self._navigation_tree, update, context
        )
        if not showed:
            await update.effective_message.reply_text("Недостаточно прав для выполнения команды 😢")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self._navigation.process_callback(
                update,
                context
            )
        except Exception as e:
            await update.callback_query.answer("Упс! Произошла какая-то ошибка!")
            raise
