from datetime import datetime, timedelta

import structlog
from injector import inject

from voice_bot.db.enums import DumpStates
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.spreadsheets.models.spreadsheet_schedule_record import SpreadsheetScheduleRecord
from voice_bot.spreadsheets.schedule_table import ScheduleTableService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class SpreadsheetDumper:
    LOGGER = structlog.get_logger(class_name="SpreadsheetDumper")

    @inject
    def __init__(self, schedule_table: ScheduleTableService, schedule: ScheduleService):
        self.schedule = schedule
        self.schedule_table = schedule_table

    async def dump_schedule(self):
        dump = await self.schedule_table.dump_records(weeks=-1, from_monday=datetime.now())
        bot_lessons = await self.schedule.get_schedule(datetime.min, datetime.max)

        for lesson in bot_lessons:
            if lesson.dump_state == DumpStates.BOT_DELETED:
                continue

            dump.append(SpreadsheetScheduleRecord(
                table_name=self.schedule_table.generate_table_name(lesson.absolute_start_time - timedelta(days=lesson.absolute_start_time.weekday())),
                user_id=lesson.user.unique_name,
                is_online=False,
                day_of_the_week=lesson.absolute_start_time.weekday()+1,
                raw_time_start_time_end=f"{lesson.time_start}-{lesson.time_end}",
                time_start=lesson.time_start,
                time_end=lesson.time_end,
                absolute_start_time=lesson.absolute_start_time,
            ))

        await self.schedule_table.rewrite_all_records(dump)
        await self.LOGGER.info("dumped lessons to spreadsheets")
