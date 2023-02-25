from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.domain.context import Context
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class NextLesson(TextView):
    @inject
    def __init__(self, schedule: ScheduleService, msg_builder: MessageBuilder, context: Context):
        self._context = context
        self._msg_builder = msg_builder
        self._schedule = schedule

    async def get_title(self) -> str:
        raise RuntimeError("NextLesson is supposed to have title override")

    async def get_message_text(self) -> str:
        user = self._context.authorized_user
        is_admin = 'is_admin' in self.nav_context.context_vars
        lesson = await (self._schedule.get_next_lesson() if is_admin else self._schedule.get_next_lesson_for(user))
        if not lesson:
            return await self._msg_builder.format("Занятие.Следующее_занятие_нет")

        if is_admin:
            self._msg_builder.push_user(lesson.user)

        self._msg_builder.push("расписание_день_недели",
                               DAYS_OF_THE_WEEK[lesson.absolute_start_time.weekday() + 1].capitalize())
        self._msg_builder.push_schedule_record(lesson)
        return await self._msg_builder.format("Занятие.Следующее_занятие_учитель" if is_admin
                                              else "Занятие.Следующее_занятие")
