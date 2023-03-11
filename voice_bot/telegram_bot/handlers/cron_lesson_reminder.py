from datetime import datetime, timedelta

import structlog
from injector import inject
from telegram.ext import ContextTypes

from voice_bot.constants import REMINDERS_TEXT, REMINDER_THRESHOLD
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.reminders_service import RemindersService
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService
from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CronLessonReminder(BaseScheduleHandler):
    @inject
    def __init__(self,
                 reminders: RemindersService,
                 users: UsersService,
                 schedule: ScheduleService,
                 msg_builder: MessageBuilder,
                 dt: DatetimeService):
        self._dt = dt
        self._schedule = schedule
        self._users = users
        self._reminders = reminders
        self._msg_builder = msg_builder
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        now = self._dt.now()

        await self._remind_users(now)
        await self._remind_admins(now)

    async def _remind_users(self, at: datetime):
        fired = await self._reminders.get_fired_reminders_at(at)
        for reminder in fired:
            self._msg_builder.push_schedule(reminder.lesson)
            self._msg_builder.push("занятие_относительное_время", REMINDERS_TEXT[timedelta(minutes=reminder.minutes)])

            await self._users.send_text_message(
                reminder.chat_id,
                await self._msg_builder.format("Занятие.Напоминание_о_занятии_ученик")
            )

    async def _remind_admins(self, at: datetime):
        next_lesson = await self._schedule.get_next_lesson()

        if not next_lesson:
            return

        for admin in (await self._users.get_all_admins()):
            reminders = await self._reminders.get_active_reminders_for(admin)
            if not reminders:
                continue

            reminder = self._get_fired_reminder(at, next_lesson.absolute_start_time, reminders)

            if reminder:
                user = await self._users.get_user_by_id(next_lesson.user_id)

                self._msg_builder.push_user(user)
                self._msg_builder.push_schedule_record(next_lesson)
                self._msg_builder.push("занятие_относительное_время", REMINDERS_TEXT[reminder])

                await self._users.send_text_message(
                    admin,
                    await self._msg_builder.format("Занятие.Напоминание_о_занятии_учитель")
                )

    @staticmethod
    def _get_fired_reminder(on_time: datetime, lesson_start_time: datetime,
                            reminders: list[timedelta]) -> timedelta | None:
        fired_reminders = [*filter(
            lambda x: lesson_start_time - x - REMINDER_THRESHOLD <= on_time and
                      REMINDER_THRESHOLD + lesson_start_time - on_time >= x,
            reminders
        )]

        if len(fired_reminders) == 0:
            return None

        return min(fired_reminders)
