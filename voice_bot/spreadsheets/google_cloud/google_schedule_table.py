import math
from collections import defaultdict
from datetime import timedelta, date, datetime
from typing import Iterable

from injector import inject

from voice_bot.misc.simple_cache import simplecache
from voice_bot.spreadsheets.exceptions import ScheduleWeekIsNotFoundException
from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.spreadsheets.models.spreadsheet_schedule_record import SpreadsheetScheduleRecord
from voice_bot.spreadsheets.schedule_table import ScheduleTableService


class GoogleScheduleTableService(ScheduleTableService):
    @inject
    def __init__(self, gspread: GspreadClient):
        self._gspread = gspread

    async def get_standard_schedule(self) -> dict[str, list[SpreadsheetScheduleRecord]]:
        return await self._get_schedule_from_table(self.STANDARD_SCHEDULE_TABLE_NAME)

    @simplecache("google_schedule", timedelta(minutes=60))
    async def _get_schedule_from_table(
        self,
        table_name: str,
        monday: datetime | None = None,
    ) -> dict[str, list[SpreadsheetScheduleRecord]]:
        return await self._get_schedule_from_table_nocache(table_name, monday)

    async def _get_schedule_from_table_nocache(
            self, table_name: str,
            monday: datetime | None = None, get_dict: bool = True
    ) -> dict[str, list[SpreadsheetScheduleRecord]] | list[SpreadsheetScheduleRecord]:
        worksheet = await self._gspread.get_schedule_worksheet(table_name)
        values = worksheet.get_values()

        if monday:
            monday = monday - timedelta(days=monday.weekday())

        res: dict[str, list[SpreadsheetScheduleRecord]] | list[SpreadsheetScheduleRecord]
        if get_dict:
            res = {}
        else:
            res = list[SpreadsheetScheduleRecord]()

        for row in values[2:]:
            times = row[0].split("-")
            start_time, end_time = times[0], times[1]

            for day, lesson in enumerate(row[1:]):
                if not lesson:
                    continue

                lesson_split = lesson.split()
                schedule_record = SpreadsheetScheduleRecord(
                    table_name=table_name,
                    user_id=lesson_split[0],
                    raw_time_start_time_end = row[0],
                    time_start=start_time,
                    time_end=end_time,
                    day_of_the_week=day + 1,
                    absolute_start_time=(
                        self._get_start_datetime(start_time, monday + timedelta(days=day))
                        if monday else None
                    ),
                    is_online=len(lesson_split) > 1,
                )

                if get_dict:
                    if schedule_record.user_id not in res:
                        res[schedule_record.user_id] = list[SpreadsheetScheduleRecord]()

                    res[schedule_record.user_id].append(schedule_record)
                    continue

                res.append(schedule_record)

        if get_dict:
            for key in res:
                res[key].sort(key=lambda x: x.day_of_the_week)

        return res

    @staticmethod
    def _get_start_datetime(time_start: str, day: datetime) -> datetime:
        start_hours, start_minutes = list(map(int, time_start.split(':')))
        return datetime(year=day.year, month=day.month, day=day.day, hour=start_hours, minute=start_minutes)

    async def get_schedule_for_timespan(
        self,
        day_start: date,
        day_end: date,
    ) -> dict[str, list[SpreadsheetScheduleRecord]]:
        pass

    async def create_schedule_sheet_for_week(self, monday: date):
        new_sheet_title = self.generate_table_name(monday)
        all_sheets = await self._get_all_schedule_sheet_names()

        if new_sheet_title in all_sheets:
            raise RuntimeError(f"Sheet with name {new_sheet_title} already exist")

        self._gspread.gs_schedule_sheet.worksheet(self.STANDARD_SCHEDULE_TABLE_NAME).duplicate(
            insert_sheet_index=1,
            new_sheet_name=new_sheet_title
        )

    async def _get_all_schedule_sheet_names(self, from_monday: date | None = None, weeks: int = -1) -> set[str]:
        res = set[str]()

        name_filter: set[str] | None = None
        if from_monday:
            name_filter = set[str]()
            for _ in range(weeks + 1):
                name_filter.add(self.generate_table_name(from_monday))
                from_monday += timedelta(days=7)

        for worksheet in self._gspread.gs_schedule_sheet.worksheets():
            if worksheet.title.lower() == self.STANDARD_SCHEDULE_TABLE_NAME.lower():
                continue

            if name_filter:
                if worksheet.title in name_filter:
                    res.add(worksheet.title)
                continue

            res.add(worksheet.title)

        return res

    async def get_all_schedule_sheet_mondays(self, weeks_back: int, weeks_forward: int) -> set[date]:
        res = set[date]()

        sheets = await self._get_all_schedule_sheet_names()

        current_monday = date.today() - timedelta(days=date.today().weekday()) - timedelta(days=-7 * weeks_back)
        finish_monday = current_monday + timedelta(days=7 * (weeks_back + weeks_forward))

        while current_monday <= finish_monday:
            if self.generate_table_name(current_monday) in sheets:
                res.add(current_monday)

            current_monday += timedelta(days=7)

        return res

    async def dump_records(self, **kwargs) -> list[SpreadsheetScheduleRecord]:
        if "from_monday" not in kwargs or "weeks" not in kwargs:
            raise KeyError("GoogleScheduleTableService.dump_records requires 'from_monday' and 'weeks' kwargs")

        from_monday: datetime = kwargs['from_monday']
        weeks: int = kwargs['weeks']

        res:  list[SpreadsheetScheduleRecord] = await self._get_schedule_from_table_nocache(
            self.STANDARD_SCHEDULE_TABLE_NAME, get_dict=False
        )

        sheets: dict[datetime, str] = {}
        for sheet_name in await self._get_all_schedule_sheet_names(from_monday=from_monday, weeks=weeks):
            day, month = sheet_name.split('-')[0].split('.')
            sheets[datetime(year=2023, month=int(month), day=int(day))] = sheet_name

        for i in range(weeks):
            current_monday = from_monday + timedelta(days=7 * i)
            sheet_name = sheets[datetime(year=2023, month=current_monday.month, day=current_monday.day)]
            res += await self._get_schedule_from_table_nocache(sheet_name, get_dict=False, monday=current_monday)

        return res

    async def rewrite_all_records(self, records: list[SpreadsheetScheduleRecord]):
        first_column = (await self._gspread.get_schedule_worksheet(self.STANDARD_SCHEDULE_TABLE_NAME)).col_values(1)[2:]

        await self._rewrite_schedule_table(
            self.STANDARD_SCHEDULE_TABLE_NAME,
            self._put_records_into_table_layout(
                filter(lambda x: not x.absolute_start_time and not x.to_delete, records),
                first_column
            )
        )

        min_time = min((record.absolute_start_time or datetime.max for record in records))
        max_time = max((record.absolute_start_time or datetime.min for record in records))

        if min_time == datetime.max or max_time == datetime.min:
            return

        weeks = math.ceil((max_time - min_time).days / 7)

        monday = min_time - timedelta(days=min_time.weekday(),
                                      hours=min_time.hour, minutes=min_time.minute, seconds=min_time.second)
        saturday = monday + timedelta(days=7)

        for _ in range(weeks):
            await self._rewrite_schedule_table(
                self.generate_table_name(monday),
                self._put_records_into_table_layout(
                    filter(
                        lambda x: (monday <= (x.absolute_start_time or datetime.max) <= saturday) and not x.to_delete,
                        records
                    ),
                    first_column
                ),
                monday=monday
            )
            monday += timedelta(days=7)
            saturday += timedelta(days=7)

    def _put_records_into_table_layout(self, records: Iterable[SpreadsheetScheduleRecord],
                                       first_column: list[str]) -> list[list[str]]:
        res_dict: dict[str, list[str]] = {key: 7 * [''] for key in first_column}

        for record in records:
            res_dict[record.raw_time_start_time_end][record.day_of_the_week-1] = self._record_to_cell(record)

        return [res_dict[key] for key in first_column]

    @staticmethod
    def _record_to_cell(record: SpreadsheetScheduleRecord) -> str:
        if record.is_online:
            return f"{record.user_id} (онлайн)"

        return record.user_id

    async def _rewrite_schedule_table(self, sheet_name: str, content: list[list[str]], monday: datetime | None = None):
        worksheet = await self._gspread.get_schedule_worksheet(sheet_name)
        update = [{
            'range': 'B3:H12',
            'values': content,
        }]
        if monday:
            days_of_the_week = []
            for i in range(7):
                days_of_the_week.append(monday.strftime('%d.%m.%Y'))
                monday += timedelta(days=1)
            update.append({
                'range': 'B2:H2',
                'values': [days_of_the_week]
            })
        worksheet.batch_update(update)
