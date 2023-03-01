from datetime import timedelta

import structlog
from injector import inject

from voice_bot.constants import REMINDERS_OPTIONS
from voice_bot.db.update_session import UpdateSession
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.telegram_bot.telegram_bot_proxy import TelegramBotProxy
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class AdminsService:
    @inject
    def __init__(self, params: ParamsTableService, tg_bot_proxy: TelegramBotProxy, session: UpdateSession):
        self._tg_bot_proxy = tg_bot_proxy
        self._params = params
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def send_message_to_admins(self, text: str):
        await self._tg_bot_proxy.bot.send_message(
            await self._params.get_param("преподаватель_chat_id"),
            text
        )

    async def get_reminders(self) -> set[timedelta]:
        res = set[timedelta]()

        reminders_str = await self._params.get_param("преподаватель_напоминания")

        if not reminders_str:
            return res

        for reminder_str in reminders_str.split(', '):
            if reminder_str not in REMINDERS_OPTIONS:
                await self._logger.warning("Reminder key missing", reminder_str=reminder_str)
                continue

            res.add(REMINDERS_OPTIONS[reminder_str])

        return res

    @staticmethod
    def _reminders_to_str(reminders: set[timedelta]) -> str:
        res = []

        for k, v in REMINDERS_OPTIONS.items():
            if v in reminders:
                res.append(k)

        return ', '.join(res)

    async def switch_reminder(self, reminder: timedelta):
        reminders = await self.get_reminders()
        if reminder in reminders:
            reminders.remove(reminder)
        else:
            reminders.add(reminder)

        await self._params.rewrite_param("преподаватель_напоминания", self._reminders_to_str(reminders))
