from injector import inject

from voice_bot.services.reminders_service import RemindersService
from voice_bot.telegram_bot.claims.authorized_user import AuthorizedUser
from voice_bot.telegram_bot.navigation.base_classes import BaseAction
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class SetReminder(BaseAction):
    @inject
    def __init__(self, reminders_service: RemindersService, auth_user: AuthorizedUser):
        self._user = auth_user.get_authorized_user()
        self._reminders_service = reminders_service

    async def handle_action(self):
        reminder = self.nav_context.context_vars["reminder"]

        if "is_admin" in self.nav_context.context_vars:
            await self._reminders_service.switch_reminder_admin(reminder)
        else:
            await self._reminders_service.switch_reminder_for(self._user, reminder)

    async def get_title(self) -> str:
        reminder = self.nav_context.context_vars["reminder"]

        if "is_admin" in self.nav_context.context_vars:
            state = await self._reminders_service.get_reminder_state_admin(reminder)
        else:
            state = self._reminders_service.get_reminder_state_for(self._user, reminder)

        return f"{'✅' if state else '❌'} {self.nav_context.context_vars['title']}"
