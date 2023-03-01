from injector import inject

from voice_bot.domain.services.spreadsheet_sync_service import SpreadsheetSyncService
from voice_bot.telegram_bot.navigation.base_classes import BaseAction
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class PerformSync(BaseAction):
    @inject
    def __init__(self, sync: SpreadsheetSyncService):
        self._sync = sync

    async def handle_action(self):
        await self._sync.perform_sync()
        await self.update.callback_query.answer("Синхронизация проведена успешно!")

    async def get_title(self) -> str:
        raise RuntimeError("PerformSync is not supposed to generate its own title")
