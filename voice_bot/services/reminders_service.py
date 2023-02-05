from datetime import timedelta

from injector import inject

from voice_bot.constants import REMINDERS_OPTIONS
from voice_bot.services.admins_service import AdminsService
from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.users_table import UsersTableService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class RemindersService:
    @inject
    def __init__(self, users_table: UsersTableService, admins_service: AdminsService):
        self._admins_service = admins_service
        self._users_table = users_table

    @staticmethod
    def _get_reminder_by_key(reminder_key: str) -> timedelta:
        return REMINDERS_OPTIONS[reminder_key]

    async def switch_reminder_for(self, user: User, reminder_type: str):
        reminder = self._get_reminder_by_key(reminder_type)
        if reminder in user.schedule_reminders:
            user.schedule_reminders.remove(reminder)
        else:
            user.schedule_reminders.add(reminder)
        await self._users_table.rewrite_user(user)

    async def switch_reminder_admin(self, reminder_type: str):
        reminder = self._get_reminder_by_key(reminder_type)
        await self._admins_service.switch_reminder(reminder)

    def get_reminder_state_for(self, user: User, reminder_type: str) -> bool:
        return self._get_reminder_by_key(reminder_type) in user.schedule_reminders

    async def get_reminder_state_admin(self, reminder_type: str) -> bool:
        reminder = self._get_reminder_by_key(reminder_type)
        reminders = await self._admins_service.get_reminders()
        return reminder in reminders
