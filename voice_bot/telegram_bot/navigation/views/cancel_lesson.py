from datetime import timedelta, datetime

from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.db.models import ScheduleRecord
from voice_bot.domain.context import Context
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab, _TreeEntry
from voice_bot.telegram_bot.navigation.views.admin_cancellation_confirm import CancellationConfirmView
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class StudentCancelLessonView(TextView):
    _CONFIRMATION = "confirm"
    _CANCELED = "canceled"

    _YES = "yes"
    _NO = "no"

    @inject
    def __init__(self,
                 schedule: ScheduleService,
                 context: Context,
                 msg: MessageBuilder,
                 dt: DatetimeService,
                 users: UsersService):
        super().__init__()
        self._users = users
        self._dt = dt
        self._msg = msg
        self._schedule = schedule
        self._context = context

    async def get_message_text(self) -> str:
        match self.get_view_kwarg("_state", False):
            case self._CANCELED:
                lesson_id: int = self.get_view_kwarg("_lesson_id", False)
                self._msg.push_schedule_record(await self._schedule.get_lesson_by_id(lesson_id))
                return await self._msg.format("Отмена.Запрос_отправлен")
            case self._CONFIRMATION:
                return await self._msg.format("Занятие.Подтверждение_отмены")
            case _:
                return await self._msg.format("Отмена.Список_на_отмену")

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", kwargs={"_back": "y"})}
        match self.get_view_kwarg("_state", False):
            case self._CANCELED:
                return res
            case self._CONFIRMATION:
                return {
                    "_no": _ButtonStab((100, 0), "Нет", kwargs={"_action": self._NO}),
                    "_yes": _ButtonStab((100, 10), "Да", kwargs={"_action": self._YES})}
            case _:
                user = self._context.authorized_user
                now = self._dt.now() + timedelta(hours=24)
                lessons = await self._schedule.get_schedule_for(now, now + timedelta(days=14), user)
                for i, lesson in enumerate(lessons):
                    self._msg.push_schedule(lesson)
                    res["_" + str(lesson.id)] = _ButtonStab(
                        (100 + i, 0),
                        await self._msg.format("Отмена.Строка_занятия_ученик"),
                        kwargs={"_lesson_id": lesson.id, "_user_id": user.id, "_state": self._CONFIRMATION})
                return res

    async def handle(self) -> NavigationContext | None:
        if self.get_view_kwarg("_back"):
            self.erase_view_kwargs()
            self.nav_context.tree_path.pop()
            return self.nav_context

        match self.get_view_kwarg("_action"):
            case self._YES:
                await self._users.send_menu_to_admins([_TreeEntry(CancellationConfirmView)], {
                    "lesson_id": self.get_view_kwarg("_lesson_id", False),
                    "user_id": self.get_view_kwarg("_user_id", False),
                })
                self.set_view_kwarg("_state", self._CANCELED)
            case self._NO:
                self.set_view_kwarg("_state", None)
        return self.nav_context


@telegramupdate
class AdminCancelLessonView(BaseView):
    _SELECT_DAY = "days"
    _SELECT_LESSON = "lessons"
    _CONFIRM = "confirm"

    _BACK = "back"
    _YES = "yes"

    @inject
    def __init__(self, msg: MessageBuilder, schedule: ScheduleService, dt: DatetimeService, users: UsersService):
        super().__init__()
        self._users = users
        self._dt = dt
        self._schedule = schedule
        self._msg = msg

        self._lesson_cache: ScheduleRecord | None = None

    async def get_message_text(self) -> str:
        match self.get_view_kwarg("_state", False):
            case self._SELECT_DAY:
                monday: datetime = self.get_view_kwarg("_monday", False)
                return f"Неделя {self._monday_to_week_str(monday)}, выбери день"
            case self._SELECT_LESSON:
                day: datetime = self.get_view_kwarg("_day", False)
                return f"{DAYS_OF_THE_WEEK[day.weekday()+1].capitalize()} {day.strftime('%d.%m.%Y')}, выбери занятие"
            case self._CONFIRM:
                lesson = await self._fetch_lesson_from_kwargs()
                self._msg.push_user(lesson.user)
                self._msg.push_schedule(lesson)
                return await self._msg.format("Занятие.Диалог_отмены")
            case _:
                return "Выбери неделю"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", kwargs={"_action": self._BACK})}
        match self.get_view_kwarg("_state", False):
            case self._SELECT_DAY:
                monday: datetime = self.get_view_kwarg("_monday", False)
                for i in range(7):
                    res[f"_weekday+{i}"] = _ButtonStab(
                        (100 + i, 0),
                        f"{DAYS_OF_THE_WEEK[i+1].capitalize()} ({(monday + timedelta(days=i)).strftime('%d.%m')})",
                        kwargs={"_day": monday + timedelta(days=i), "_state": self._SELECT_LESSON}
                    )
            case self._SELECT_LESSON:
                day: datetime = self.get_view_kwarg("_day", False)
                lessons = await self._schedule.get_schedule(day, day + timedelta(hours=23, minutes=50))
                for i, lesson in enumerate(lessons):
                    self._msg.push_user(lesson.user)
                    self._msg.push_schedule(lesson)
                    res[f"_lesson{i}"] = _ButtonStab(
                        (100 + i, 0),
                        await self._msg.format("Отмена.Строка_занятия_админ"),
                        kwargs={"_lesson_id": lesson.id, "_state": self._CONFIRM}
                    )
            case self._CONFIRM:
                lesson = await self._fetch_lesson_from_kwargs()
                return {
                    "_yes": _ButtonStab(
                        (100, 0),
                        "Отменить урок",
                        kwargs={"_action": self._YES, "_lesson_id": lesson.id, "_user_id": lesson.user_id}),
                    "_no": _ButtonStab((110, 0), "Назад", kwargs={"_action": self._BACK})
                }
            case _:
                now = self._dt.now()
                monday = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second)
                for i in range(4):
                    res[f"_this_week+{i}"] = _ButtonStab(
                        (100 + i, 0),
                        self._monday_to_week_str(monday),
                        kwargs={"_monday": monday, "_state": self._SELECT_DAY})
                    monday += timedelta(days=7)

        return res

    async def get_title(self) -> str:
        raise RuntimeError("no title")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case self._BACK:
                match self.get_view_kwarg("_state", False):
                    case self._CONFIRM:
                        self.set_view_kwarg("_state", self._SELECT_LESSON)
                    case self._SELECT_LESSON:
                        self.get_view_kwarg("_day")
                        self.set_view_kwarg("_state", self._SELECT_DAY)
                    case self._SELECT_DAY:
                        self.get_view_kwarg("_monday")
                        self.set_view_kwarg("_state", None)
                    case _:
                        self.erase_view_kwargs()
                        self.nav_context.tree_path.pop()
            case self._YES:
                user_id = self.get_view_kwarg("_user_id")
                lesson = await self._fetch_lesson_from_kwargs()
                await self._schedule.cancel_lesson(lesson.id)
                self._msg.push_schedule(lesson)
                await self._users.send_template(
                    await self._users.get_user_by_id(user_id), "Занятие.Отменено_оповещение")
                await self.tg_context.popup("Занятие успешно отменено, ученику отправлено уведомление.")
                self.set_view_kwarg("_state", self._SELECT_LESSON)
        return self.nav_context

    @staticmethod
    def _monday_to_week_str(monday: datetime) -> str:
        return f"{monday.strftime('%d.%m')}-{(monday + timedelta(days=6)).strftime('%d.%m')}"

    async def _fetch_lesson_from_kwargs(self) -> ScheduleRecord:
        if not self._lesson_cache:
            self._lesson_cache = await self._schedule.get_lesson_by_id(self.get_view_kwarg("_lesson_id"))
        return self._lesson_cache
