from datetime import date, timedelta

from injector import inject

from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.params_table import ParamsTable
from voice_bot.spreadsheets.schedule_table import ScheduleTable
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class Schedule:
    @inject
    def __init__(self, schedule_table: ScheduleTable, params: ParamsTable):
        self._params = params
        self._schedule_table = schedule_table

    async def get_standard_schedule(self) -> list[ScheduleRecord]:
        return await self._get_standard_schedule_base()

    async def get_standard_schedule_for(self, user: User) -> list[ScheduleRecord]:
        return await self._get_standard_schedule_base(user.unique_id)

    async def _get_standard_schedule_base(self, for_user: str | None = None) -> list[ScheduleRecord]:
        schedule = await self._schedule_table.get_standard_schedule()
        if not for_user:
            return list[ScheduleRecord](*schedule.values())
        return schedule[for_user]

    async def create_tables_if_not_exist(self) -> bool:
        did_something = False
        weeks_forward = int(await self._params.get_param("расписание_недель_вперёд"))
        existing_tables = await self._schedule_table.get_all_schedule_sheet_mondays(0, weeks_forward)
        current_monday = date.today() - timedelta(days=date.today().weekday())
        for _ in range(weeks_forward + 1):
            if current_monday not in existing_tables:
                did_something = True
                await self._schedule_table.create_schedule_sheet_for_week(current_monday)
            current_monday += timedelta(days=7)
        return did_something

    async def get_schedule(self, date_start: date, date_end: date) -> list[ScheduleRecord]:
        return await self._get_schedule_base(date_start, date_end, None)

    async def get_schedule_for(self, date_start: date, date_end: date, user: User) -> list[ScheduleRecord]:
        return await self._get_schedule_base(date_start, date_end, user)

    async def _get_schedule_base(self, date_start: date, date_end: date,
                                 user: User | None = None) -> list[ScheduleRecord]:
        all_records = await self._schedule_table.get_schedule_for_timespan(date_start, date_end)
        res = list[ScheduleRecord](all_records[user.unique_id] if user else list(*all_records.values()))
        res.sort(key=lambda x: x.absolute_start_date)
        return res

