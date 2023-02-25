from datetime import date, timedelta

from injector import singleton, inject

from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.spreadsheets.schedule_table import ScheduleTableService


@singleton
class TablesService:
    @inject
    def __init__(self, schedule_table: ScheduleTableService, params: ParamsTableService):
        self._params = params
        self._schedule_table = schedule_table

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