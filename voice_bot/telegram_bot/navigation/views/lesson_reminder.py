from datetime import timedelta

from injector import inject

from voice_bot.constants import REMINDERS_TEXT
from voice_bot.db.models import ScheduleRecord
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab, _TreeEntry
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class StudentLessonReminderView(BaseView):
    _CAN_CANCEL_HOURS = 24  # todo пока хардкод, потом вынести в параметры

    _CANNOT_CANCEL = "no_cancel"
    _CANCEL_CONFIRM = "confirmation"
    _CANCELED = "canceled"

    _CANCEL = "cancel"
    _BACK = "back"
    _CANCEL_YES = "cancel_yes"

    @inject
    def __init__(self, schedule: ScheduleService, msg: MessageBuilder, users: UsersService):
        super().__init__()
        self._users = users
        self._msg = msg
        self._schedule = schedule

    async def get_title(self) -> str:
        raise RuntimeError("no title")

    async def get_message_text(self) -> str:
        user_id: int = self.get_view_kwarg("user_id", False)
        lesson_id: int = self.get_view_kwarg("lesson_id", False)
        reminder_for: timedelta = self.get_view_kwarg("reminder_timedelta", False)
        lesson = await self._schedule.get_lesson_by_id(lesson_id)

        if not lesson or lesson.user.id != user_id:
            return await self._lesson_not_found_text()

        match self.get_view_kwarg("_state", False):
            case self._CANCELED:
                return await self._lesson_canceled(reminder_for, lesson)
            case self._CANCEL_CONFIRM:
                return await self._lesson_cancel_confirmation_text()
            case _:
                return await self._lesson_info_text(reminder_for, lesson)

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        state = self.get_view_kwarg("_state", False)
        reminder_for: timedelta = self.get_view_kwarg("reminder_timedelta", False)
        match state:
            case self._CANCELED:
                return {}
            case self._CANCEL_CONFIRM:
                return {
                    "_no": _ButtonStab((100, 0), "Нет", {"_action": self._BACK}),
                    "_yes": _ButtonStab((100, 10), "Да", {"_action": self._CANCEL_YES})
                }
            case _:
                if reminder_for.total_seconds() < 60 * 60 * self._CAN_CANCEL_HOURS:
                    return {}
                return {
                    "_cancel_lesson": _ButtonStab((100, 0), "Отменить занятие", {"_action": self._CANCEL})
                }

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case self._BACK:
                self.set_view_kwarg("_state", None)
            case self._CANCEL:
                self.set_view_kwarg("_state", self._CANCEL_CONFIRM)
            case self._CANCEL_YES:
                await self._users.send_menu_to_admins([_TreeEntry(CancellationConfirmView)], {
                    "lesson_id": self.get_view_kwarg("lesson_id", False),
                    "user_id": self.get_view_kwarg("user_id", False),
                })
                self.set_view_kwarg("_state", self._CANCELED)
        return self.nav_context

    async def _lesson_not_found_text(self) -> str:
        return await self._msg.format("Занятие.Уже_отменено")

    async def _lesson_info_text(self, reminder_for: timedelta, lesson: ScheduleRecord) -> str:
        self._msg.push_schedule(lesson)
        self._msg.push("занятие_относительное_время", REMINDERS_TEXT[reminder_for])
        return await self._msg.format("Занятие.Напоминание_о_занятии_ученик")

    async def _lesson_canceled(self, reminder_for: timedelta, lesson: ScheduleRecord) -> str:
        self._msg.push_schedule(lesson)
        self._msg.push("занятие_относительное_время", REMINDERS_TEXT[reminder_for])
        return await self._msg.format("Занятие.Запрос_отмены_отправлен")

    async def _lesson_cancel_confirmation_text(self) -> str:
        return await self._msg.format("Занятие.Подтверждение_отмены")


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
                "_no": _ButtonStab((0, 0), "Нет", {"_action": self._YES}),
                "_yes": _ButtonStab((0, 10), "Да, отменяем", {"_action": self._YES})
            }
        return {}

    async def get_title(self) -> str:
        raise RuntimeError("no title")

    async def handle(self) -> NavigationContext | None:
        lesson_id: int = self.get_view_kwarg("lesson_id", False)
        user_id: int = self.get_view_kwarg("user_id", False)
        match self.get_view_kwarg("_action"):
            case self._YES:
                await self._schedule.cancel_lesson(lesson_id, user_id)
                user = await self._users.get_user_by_id(user_id)
                lesson = await self._schedule.get_lesson_by_id(lesson_id)
                self._msg.push_schedule(lesson)
                await self._users.send_text_message(user, "")
                self.set_view_kwarg("_state", self._CANCELED)
            case self._NO:
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
