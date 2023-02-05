from datetime import datetime, timedelta

import structlog
from injector import inject
from telegram.ext import ContextTypes

from voice_bot.constants import REMINDERS_TEXT, REMINDER_THRESHOLD
from voice_bot.services.admins_service import AdminsService
from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.schedule_service import ScheduleService
from voice_bot.services.users_service import UsersService
from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CronLessonReminder(BaseScheduleHandler):
    @inject
    def __init__(self, users: UsersService, schedule: ScheduleService,
                 msg_builder: MessageBuilder, admins: AdminsService):
        self._admins = admins
        self._msg_builder = msg_builder
        self._schedule = schedule
        self._users = users
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        await self.remind_users()
        await self.remind_admin()

    async def remind_users(self):
        now = datetime.now()
        users = await self._users.get_authorized_users()

        reminded = 0

        for user in users:
            if len(user.schedule_reminders) == 0:
                continue

            next_lesson = await self._schedule.get_next_lesson_for(user)

            if not next_lesson:
                continue

            alarmed = self._get_fired_reminder(now, next_lesson.absolute_start_date, user.schedule_reminders)

            if alarmed:
                self._msg_builder.push_user(user)
                self._msg_builder.push_schedule_record(next_lesson)
                self._msg_builder.push("занятие_относительное_время", REMINDERS_TEXT[alarmed])

                await self._users.send_message(
                    user,
                    await self._msg_builder.format("Занятие.Напоминание_о_занятии_ученик")
                )

                reminded += 1

            if reminded:
                await self._logger.ainfo("Users reminded about next lessons", users_reminded=reminded)

    async def remind_admin(self):
        now = datetime.now()

        next_lesson = await self._schedule.get_next_lesson()

        if not next_lesson:
            return

        alarmed = self._get_fired_reminder(now, next_lesson.absolute_start_date, await self._admins.get_reminders())

        if alarmed:
            user = await self._users.get_user_by_id(next_lesson.user_id)

            self._msg_builder.push_user(user)
            self._msg_builder.push_schedule_record(next_lesson)
            self._msg_builder.push("занятие_относительное_время", REMINDERS_TEXT[alarmed])

            await self._admins.send_message_to_admin(
                await self._msg_builder.format("Занятие.Напоминание_о_занятии_учитель")
            )

    @staticmethod
    def _get_fired_reminder(on_time: datetime, lesson_start_time: datetime,
                            reminders: set[timedelta]) -> timedelta | None:
        fired_reminders = [*filter(
            lambda x: lesson_start_time - x - REMINDER_THRESHOLD <= on_time and
                      REMINDER_THRESHOLD + lesson_start_time - on_time >= x,
            reminders
        )]

        if len(fired_reminders) == 0:
            return None

        return min(fired_reminders)
