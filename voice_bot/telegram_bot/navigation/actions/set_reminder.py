from injector import inject

from voice_bot.domain.context import Context
from voice_bot.domain.services.reminders_service import RemindersService
from voice_bot.telegram_bot.navigation.base_classes import BaseAction
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class SetReminder(BaseAction):
    @inject
    def __init__(self, reminders_service: RemindersService, context: Context):
        super().__init__()
        self._user = context.authorized_user
        self._reminders_service = reminders_service

    async def handle_action(self):
        reminder = self.entry.context_vars["reminder"]
        await self._reminders_service.switch_reminder_for(self._user, reminder)

    async def get_title(self) -> str:
        reminder = self.entry.context_vars["reminder"]
        state = await self._reminders_service.get_reminder_state_for(self._user, reminder)
        return f"{'✅' if state else '❌'} {self.entry.context_vars['title']}"
