from itertools import groupby
from typing import Iterable

from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.db.models import ScheduleRecord
from voice_bot.domain.context import Context
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class StandardSchedule(TextView):
    @inject
    def __init__(self, schedule: ScheduleService, msg_builder: MessageBuilder, context: Context):
        super().__init__()
        self._user = context.authorized_user
        self._msg_builder = msg_builder
        self._schedule = schedule

    async def get_title(self) -> str:
        raise RuntimeError("StandardSchedule is supposed to have title override")

    async def get_message_text(self) -> str:
        reply = list[str]()

        schedule = await self._schedule.get_standard_schedule_for(self._user)

        reply.append(await self._msg_builder.format("Расписание.Заглавие_стандартного_расписания"))

        for day, lessons in groupby(schedule, lambda x: x.day_of_the_week):
            lessons: Iterable[ScheduleRecord]

            self._msg_builder.push("расписание_день_недели", DAYS_OF_THE_WEEK[day + 1].capitalize())

            reply.append('')
            reply.append(await self._msg_builder.format("Занятие.Строка_с_днём_недели"))

            for lesson in lessons:
                self._msg_builder.push_schedule_record(lesson)
                reply.append(await self._msg_builder.format("Занятие.Строка_расписания"))

        return "\n".join(reply)
