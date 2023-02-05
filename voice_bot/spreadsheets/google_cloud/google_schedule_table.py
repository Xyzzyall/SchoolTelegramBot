from collections import defaultdict
from datetime import timedelta, date, datetime

from injector import inject

from voice_bot.spreadsheets.exceptions import ScheduleWeekIsNotFoundException
from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.spreadsheets.schedule_table import ScheduleTableService


class GoogleScheduleTableService(ScheduleTableService):
    _STANDARD_SCHEDULE_TABLE_NAME = "Стандарт"

    @inject
    def __init__(self, gspread: GspreadClient):
        self._gspread = gspread

    async def get_standard_schedule(self) -> dict[str, list[ScheduleRecord]]:
        return await self._get_schedule_from_table(self._STANDARD_SCHEDULE_TABLE_NAME)

    @simplecache("google_schedule", timedelta(minutes=60))
    async def _get_schedule_from_table(
        self,
        table_name: str,
        monday: date | None = None,
    ) -> dict[str, list[ScheduleRecord]]:
        values = self._gspread.gs_schedule_sheet.worksheet(table_name).get_values()
        res = dict[str, list[ScheduleRecord]]()

        for row in values[2:]:
            times = row[0].split("-")
            start_time, end_time = times[0], times[1]
            for day, lesson in enumerate(row[1:]):
                if not lesson:
                    continue
                lesson_split = lesson.split(' ')
                schedule_record = ScheduleRecord(
                    user_id=lesson_split[0],
                    time_start=start_time,
                    time_end=end_time,
                    day_of_the_week=day + 1,
                    absolute_start_date=(
                        self._get_start_datetime(start_time, monday + timedelta(days=day))
                        if monday else None
                    ),
                    is_online=len(lesson_split) > 1,
                )
                if schedule_record.user_id not in res:
                    res[schedule_record.user_id] = list[ScheduleRecord]()
                res[schedule_record.user_id].append(schedule_record)

        for key in res:
            res[key].sort(key=lambda x: x.day_of_the_week)

        return res

    @staticmethod
    def _get_start_datetime(time_start: str, day: date) -> datetime:
        start_hours, start_minutes = list(map(int, time_start.split(':')))
        return datetime(year=day.year, month=day.month, day=day.day, hour=start_hours, minute=start_minutes)

    @staticmethod
    def _generate_table_name(monday: date) -> str:
        return f"{monday.strftime('%d.%m')}-{(monday+timedelta(days=6)).strftime('%d.%m')}"

    async def get_schedule_for_timespan(
            self, day_start: date, day_end: date
    ) -> dict[str, list[ScheduleRecord]]:
        res = defaultdict[str, list[ScheduleRecord]](lambda: list[ScheduleRecord]())
        all_sheets = await self._get_all_schedule_sheets()

        start_monday = day_start - timedelta(days=day_start.weekday())
        end_monday = day_end - timedelta(days=day_end.weekday())
        current_week_monday = start_monday

        while current_week_monday <= end_monday:
            table_name = self._generate_table_name(current_week_monday)
            if table_name not in all_sheets:
                raise ScheduleWeekIsNotFoundException(f"Table with name '{table_name}' is not found")
            current_week_schedule = await self._get_schedule_from_table(table_name, monday=current_week_monday)
            for user_id, records in current_week_schedule.items():
                for record in records:
                    if (
                        record.absolute_start_date < datetime.combine(day_start, datetime.min.time())
                        or record.absolute_start_date > datetime.combine(day_end, datetime.max.time())
                    ):
                        continue
                    res[user_id].append(record)
            current_week_monday += timedelta(days=7)
        return dict[str, list[ScheduleRecord]](res)

    async def create_schedule_sheet_for_week(self, monday: date):
        new_sheet_title = self._generate_table_name(monday)
        all_sheets = await self._get_all_schedule_sheets()

        if new_sheet_title in all_sheets:
            raise RuntimeError(f"Sheet with name {new_sheet_title} already exist")

        self._gspread.gs_schedule_sheet.worksheet(self._STANDARD_SCHEDULE_TABLE_NAME).duplicate(
            insert_sheet_index=1,
            new_sheet_name=new_sheet_title
        )

    async def _get_all_schedule_sheets(self) -> set[str]:
        res = set[str]()

        for worksheet in self._gspread.gs_schedule_sheet.worksheets():
            if worksheet.title.lower() == self._STANDARD_SCHEDULE_TABLE_NAME.lower():
                continue
            res.add(worksheet.title)

        return res

    async def get_all_schedule_sheet_mondays(self, weeks_back: int, weeks_forward: int) -> set[date]:
        res = set[date]()

        sheets = await self._get_all_schedule_sheets()

        current_monday = date.today() - timedelta(days=date.today().weekday()) - timedelta(days=-7 * weeks_back)
        finish_monday = current_monday + timedelta(days=7 * (weeks_back + weeks_forward))

        while current_monday <= finish_monday:
            if self._generate_table_name(current_monday) in sheets:
                res.add(current_monday)
            current_monday += timedelta(days=7)
        return res
