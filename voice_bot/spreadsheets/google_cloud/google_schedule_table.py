from datetime import datetime, timedelta

from voice_bot.spreadsheets.google_cloud.gspread import gs_sheet
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.spreadsheets.schedule_table import ScheduleTable


class GoogleScheduleTable(ScheduleTable):

    async def get_standard_schedule(self) -> dict[str, list[ScheduleRecord]]:
        return await self._get_schedule_from_table("Стандартное расписание")

    @simplecache("google_schedule_{}", timedelta(minutes=10))
    async def _get_schedule_from_table(self, table_name: str) -> dict[str, list[ScheduleRecord]]:
        values = gs_sheet.worksheet(table_name).get_values()
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
                    is_online=len(lesson_split) > 1
                )
                if schedule_record.user_id not in res:
                    res[schedule_record.user_id] = list[ScheduleRecord]()
                res[schedule_record.user_id].append(schedule_record)

        for key in res:
            res[key].sort(key=lambda x: x.day_of_the_week)

        return res

    async def get_schedule_for_timespan(self, day_start: datetime, day_end: datetime) -> dict[str, list[ScheduleRecord]]:
        pass

