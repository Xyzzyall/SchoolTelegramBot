from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.domain.services.cache_service import CacheService
from voice_bot.domain.services.reminders_service import RemindersService
from voice_bot.domain.services.spreadsheet_sync_service import SpreadsheetSyncService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdXxx(BaseUpdateHandler):
    @inject
    def __init__(self,
                 users: UsersService,
                 sync: SpreadsheetSyncService,
                 cache: CacheService,
                 reminders: RemindersService):
        self._reminders = reminders
        self._cache = cache
        self._sync = sync
        self._users = users

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.username != 'xyzzyall':
            await update.effective_message.reply_text("💩")
            return

        if len(context.args) == 0:
            await update.effective_message.reply_text("мне ваще-то нужна команда 🙄")
            return

        match context.args[0]:
            case "sync": await self._perform_sync(update)
            case "reminders": await self._turn_on_day_reminders(update)
            case _: await update.effective_message.reply_text(f"не нашел такой команды: {context.args[0]}")

    async def _perform_sync(self, update: Update):
        self._cache.clear_all_cache()
        await self._sync.perform_sync()
        await update.effective_message.reply_text("готово")

    async def _turn_on_day_reminders(self, update: Update):
        users = await self._users.get_all_regular_users()
        for user in users:
            await self._reminders.set_reminder_state_for(user, "за сутки", True)
        await update.effective_message.reply_text("готово")
