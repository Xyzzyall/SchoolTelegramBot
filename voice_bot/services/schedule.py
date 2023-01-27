from injector import inject

from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.spreadsheets.schedule_table import ScheduleTable
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class Schedule:
    @inject
    def __init__(self, schedule_table: ScheduleTable):
        self._schedule_table = schedule_table

    async def get_standard_schedule(self) -> list[ScheduleRecord]:
        return await self._get_standard_schedule_base()

    async def get_standard_schedule_for(self, user_unique_id: str) -> list[ScheduleRecord]:
        return await self._get_standard_schedule_base(user_unique_id)

    async def _get_standard_schedule_base(self, for_user: str | None = None) -> list[ScheduleRecord]:
        schedule = await self._schedule_table.get_standard_schedule()
        if not for_user:
            return list[ScheduleRecord](*schedule.values())
        return schedule[for_user]
