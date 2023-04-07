from injector import inject

from voice_bot.db.models import ScheduleRecord
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.telegram_bot.navigation.base_classes import BaseView, _ButtonStab, NavigationContext
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CancellationConfirmView(BaseView):
    _CANCELED = "canceled"
    _NOT_CONFIRMED = "no_confirm"

    _YES = "yes"
    _NO = "no"

    @inject
    def __init__(self, schedule: ScheduleService, msg: MessageBuilder, users: UsersService):
        super().__init__()
        self._users = users
        self._msg = msg
        self._schedule = schedule

    async def get_message_text(self) -> str:
        lesson_id: int = self.get_view_kwarg("lesson_id", False)
        match self.get_view_kwarg("_state", False):
            case self._NOT_CONFIRMED:
                return await self._not_confirmed_text()
            case self._CANCELED:
                return await self._canceled_text()
            case _:
                lesson = await self._schedule.get_lesson_by_id(lesson_id)
                return await self._default_text(lesson)

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        if not self.get_view_kwarg("_state", False):
            return {
                "_no": _ButtonStab((0, 0), "Нет", {"_action": self._NO}),
                "_yes": _ButtonStab((0, 10), "Да, отменяем", {"_action": self._YES})
            }
        return {}

    async def get_title(self) -> str:
        raise RuntimeError("no title")

    async def handle(self) -> NavigationContext | None:
        lesson_id: int = self.get_view_kwarg("lesson_id", False)
        user_id: int = self.get_view_kwarg("user_id", False)
        user = await self._users.get_user_by_id(user_id)
        lesson = await self._schedule.get_lesson_by_id(lesson_id)
        match self.get_view_kwarg("_action"):
            case self._YES:
                await self._schedule.cancel_lesson(lesson_id, user_id)
                self._msg.push_schedule(lesson)
                await self._users.send_template(user, "Занятие.Запрос_отмены_ОК")
                self.set_view_kwarg("_state", self._CANCELED)
            case self._NO:
                self._msg.push_schedule(lesson)
                await self._users.send_template(user, "Занятие.Запрос_отмены_НЕ_ОК")
                self.set_view_kwarg("_state", self._NOT_CONFIRMED)
        return self.nav_context

    async def _default_text(self, lesson: ScheduleRecord):
        self._msg.push_schedule(lesson)
        self._msg.push_user(lesson.user)
        return await self._msg.format("Занятие.Запрос_отмены")

    async def _canceled_text(self):
        return await self._msg.format("Занятие.Отменено")

    async def _not_confirmed_text(self):
        return await self._msg.format("Занятие.Отмена_заблокирована")