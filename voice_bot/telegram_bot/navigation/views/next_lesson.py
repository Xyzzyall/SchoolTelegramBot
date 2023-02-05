from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.schedule_service import ScheduleService
from voice_bot.services.users_service import UsersService
from voice_bot.telegram_bot.claims.authorized_user import AuthorizedUser
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class NextLesson(TextView):
    @inject
    def __init__(self, schedule: ScheduleService, auth_user: AuthorizedUser, msg_builder: MessageBuilder, users: UsersService):
        self._users = users
        self._msg_builder = msg_builder
        self._auth_user = auth_user
        self._schedule = schedule

    async def get_title(self) -> str:
        raise RuntimeError("NextLesson is supposed to have title override")

    async def get_message_text(self) -> str:
        user = self._auth_user.get_authorized_user()
        is_admin = 'is_admin' in self.nav_context.context_vars
        lesson = await (self._schedule.get_next_lesson() if is_admin else self._schedule.get_next_lesson_for(user))
        if not lesson:
            return await self._msg_builder.format("Занятие.Следующее_занятие_нет")

        if not user:
            user = await self._users.get_user_by_id(lesson.user_id)
        self._msg_builder.push("расписание_день_недели",
                               DAYS_OF_THE_WEEK[lesson.absolute_start_date.weekday() + 1].capitalize())
        self._msg_builder.push_user(user)
        self._msg_builder.push_schedule_record(lesson)
        return await self._msg_builder.format("Занятие.Следующее_занятие_учитель" if is_admin
                                              else "Занятие.Следующее_занятие")
