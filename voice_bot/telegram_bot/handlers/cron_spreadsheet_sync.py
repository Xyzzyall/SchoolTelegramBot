import structlog
from injector import inject
from telegram.ext import ContextTypes

from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.spreadsheet_sync_service import SpreadsheetSyncService
from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CronSpreadsheetSync(BaseScheduleHandler):
    @inject
    def __init__(self,
                 sync: SpreadsheetSyncService,
                 session: UpdateSession):
        self._session = session.session
        self._sync = sync
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self._sync.perform_sync()
        except Exception as e:
            await self._session.rollback()
            await self._logger.error("error while spreadsheet sync", exception=e)
