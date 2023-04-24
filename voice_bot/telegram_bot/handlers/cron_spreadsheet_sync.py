from injector import inject
from telegram.ext import ContextTypes

from voice_bot.domain.services.calendar_sync_service import CalendarSyncService
from voice_bot.domain.services.spreadsheet_sync_service import SpreadsheetSyncService
from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CronSpreadsheetSync(BaseScheduleHandler):
    @inject
    def __init__(self, sync: SpreadsheetSyncService):#, gc_sync: CalendarSyncService):
        #self._gc_sync = gc_sync
        self._sync = sync

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        await self._sync.perform_sync()
        #await self._gc_sync.sync()
