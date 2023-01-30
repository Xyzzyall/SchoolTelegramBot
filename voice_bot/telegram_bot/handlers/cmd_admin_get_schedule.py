from datetime import datetime
from itertools import groupby
from typing import Iterable

from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.schedule import Schedule
from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdAdminGetSchedule(BaseUpdateHandler):
    @inject
    def __init__(self, schedule: Schedule, msg_builder: MessageBuilder):
        self._msg_builder = msg_builder
        self._schedule = schedule

    # todo временные окна
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply = list[str]()
        schedule = await self._schedule.get_standard_schedule()

        timeframe = self._parse_timeframe(context)
        if timeframe:
            self._msg_builder.push("расписание_временное_окно", f"")  # todo timeframe msg
        else:
            self._msg_builder.push("расписание_временное_окно", "")

        reply.append(await self._msg_builder.format("Расписание.Заглавие_расписания"))

        for day, lessons in groupby(schedule, lambda x: x.day_of_the_week):
            lessons: Iterable[ScheduleRecord]
            self._msg_builder.push("расписание_день_недели", DAYS_OF_THE_WEEK[day].capitalize())
            reply.append(await self._msg_builder.format("Занятие.Строка_с_днём_недели"))
            for lesson in lessons:
                await self._msg_builder.push_schedule_record(lesson)
                reply.append(await self._msg_builder.format("Занятие.Учитель_строка_расписания"))

        await update.message.reply_text("\n".join(reply))

    @staticmethod
    def _parse_timeframe(context: ContextTypes.DEFAULT_TYPE) -> (datetime, datetime):  # todo
        return None
