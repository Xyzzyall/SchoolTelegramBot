from datetime import timedelta, datetime
from itertools import groupby
from typing import Iterable

from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.db.models import ScheduleRecord
from voice_bot.domain.context import Context
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, to_midnight
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class TimeBoundedSchedule(TextView):
    @inject
    def __init__(self, schedule: ScheduleService, msg_builder: MessageBuilder, users: UsersService, context: Context,
                 dt: DatetimeService):
        super().__init__()
        self._dt = dt
        self._context = context
        self._users = users
        self._msg_builder = msg_builder
        self._schedule = schedule

    async def get_title(self) -> str:
        raise RuntimeError("TimeBoundedSchedule is supposed to have title override")

    async def get_message_text(self) -> str:
        start, end = self._decode_timespan()
        self._msg_builder.push("расписание_даты_расписания", self._date_span_to_text(start, end))

        records = await self._get_records(start, end)
        if len(records) == 0:
            return await self._msg_builder.format("Расписание.Занятий_нет")

        reply = list[str]()
        reply.append(await self._msg_builder.format("Расписание.Заглавие_расписания_на_даты"))

        for day, lessons in groupby(records, lambda x: x.absolute_start_time.date()):
            day: datetime
            lessons: Iterable[ScheduleRecord]

            self._msg_builder.push("расписание_день_недели",
                                   f"{DAYS_OF_THE_WEEK[day.weekday() + 1].capitalize()} ({day.strftime('%d.%m.%Y')})")
            reply.append('')
            reply.append(await self._msg_builder.format("Занятие.Строка_с_днём_недели"))

            for lesson in lessons:
                if "is_admin" in self.entry.context_vars:
                    self._msg_builder.push_user(lesson.user)
                    self._msg_builder.push_schedule_record(lesson)

                    reply.append(await self._msg_builder.format("Занятие.Учитель_строка_расписания"))
                    continue

                self._msg_builder.push_schedule_record(lesson)
                reply.append(await self._msg_builder.format("Занятие.Строка_расписания"))

        return '\n'.join(reply)

    async def _get_records(self, date_start: datetime, date_end: datetime) -> list[ScheduleRecord]:
        user = self._context.authorized_user if "is_admin" not in self.entry.context_vars else None
        return await (self._schedule.get_schedule_for(date_start, date_end, user) if user
                      else self._schedule.get_schedule(date_start, date_end))

    def _decode_timespan(self) -> (datetime, datetime):
        time_bound = self.entry.context_vars["time_bound"]

        now = self._dt.now()
        today_begin = to_midnight(now)
        today_end = today_begin + timedelta(hours=23, minutes=59)

        match time_bound:
            case "today": return today_begin, today_end
            case "tomorrow":
                return today_begin + timedelta(days=1), today_end + timedelta(days=1)

        days = int(time_bound)
        return today_begin, today_end + timedelta(days=days)

    @staticmethod
    def _date_span_to_text(start: datetime, end: datetime) -> str:
        if start.date() == end.date():
            return f"на {start.strftime('%d.%m.%Y')}"
        return f"с {start.strftime('%d.%m.%Y')} по {end.strftime('%d.%m.%Y')}"
