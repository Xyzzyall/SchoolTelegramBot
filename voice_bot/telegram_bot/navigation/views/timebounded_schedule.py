from datetime import date, timedelta
from itertools import groupby
from typing import Iterable

from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.schedule import Schedule
from voice_bot.services.users import Users
from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.telegram_bot.claims.authorized_user import AuthorizedUser
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class TimeBoundedSchedule(TextView):
    @inject
    def __init__(self, schedule: Schedule, auth_user: AuthorizedUser, msg_builder: MessageBuilder, users: Users):
        self._users = users
        self._msg_builder = msg_builder
        self._auth_user = auth_user
        self._schedule = schedule

    async def get_title(self) -> str:
        raise RuntimeError("TimeBoundedSchedule is supposed to have title override")

    async def get_message_text(self) -> str:
        date_start, date_end = self._decode_timespan()
        self._msg_builder.push("расписание_даты_расписания", self._date_span_to_text(date_start, date_end))

        records = await self._get_records(date_start, date_end)
        if len(records) == 0:
            return await self._msg_builder.format("Расписание.Занятий_нет")

        reply = list[str]()
        reply.append(await self._msg_builder.format("Расписание.Заглавие_расписания_на_даты"))
        reply.append('')
        for day, lessons in groupby(records, lambda x: x.absolute_start_date):
            day: date
            lessons: Iterable[ScheduleRecord]
            self._msg_builder.push("расписание_день_недели",
                                   f"{DAYS_OF_THE_WEEK[day.weekday()].capitalize()} ({day.strftime('%d.%m.%Y')})")
            reply.append(await self._msg_builder.format("Занятие.Строка_с_днём_недели"))
            for lesson in lessons:
                if "is_admin" in self.nav_context.context_vars:
                    user = await self._users.get_user_by_id(lesson.user_id)
                    if not user:
                        raise RuntimeError(f"User with id={lesson.user_id} is not found")
                    self._msg_builder.push_user(user)
                    self._msg_builder.push_schedule_record(lesson)
                    reply.append(await self._msg_builder.format("Занятие.Учитель_строка_расписания"))
                    continue
                self._msg_builder.push_schedule_record(lesson)
                reply.append(await self._msg_builder.format("Занятие.Строка_расписания"))

        return '\n'.join(reply)

    async def _get_records(self, date_start: date, date_end: date) -> list[ScheduleRecord]:
        user = self._auth_user.get_authorized_user() if "is_admin" not in self.nav_context.context_vars else None
        return await (self._schedule.get_schedule_for(date_start, date_end, user) if user
                      else self._schedule.get_schedule(date_start, date_end))

    def _decode_timespan(self) -> (date, date):
        time_bound = self.nav_context.context_vars["time_bound"]
        match time_bound:
            case "today": return date.today(), date.today()
            case "tomorrow":
                tomorrow = date.today() + timedelta(days=1)
                return tomorrow, tomorrow
        days = int(time_bound)
        return date.today(), date.today() + timedelta(days=days)

    @staticmethod
    def _date_span_to_text(start: date, end: date) -> str:
        if start == end:
            return f"на {start.strftime('%d.%m.%Y')}"
        return f"с {start.strftime('%d.%m.%Y')} по {end.strftime('%d.%m.%Y')}"
