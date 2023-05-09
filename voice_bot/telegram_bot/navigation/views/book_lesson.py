from abc import ABC, abstractmethod
from datetime import timedelta, datetime

from injector import inject
from typing_extensions import override

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.db.models import User
from voice_bot.domain.context import Context
from voice_bot.domain.services.book_lesson_service import FreeLesson, BookLessonsService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, to_midnight
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab, _TreeEntry
from voice_bot.telegram_bot.services.errors_messenger import ErrorsMessenger
from voice_bot.telegram_di_scope import telegramupdate


class _BookLessonBase(BaseView, ABC):
    _CHOOSE_WEEK = "week"
    _CHOOSE_DAY = "day"
    _CHOOSE_LESSON = "lesson"
    _CONFIRM = "confirm"

    _YES = "yes"
    _BACK = "back"

    def __init__(self, dt: DatetimeService):
        super().__init__()
        self._dt = dt

    async def get_message_text(self) -> str:
        match self._get_state():
            case self._CHOOSE_WEEK:
                return "Выберите неделю"
            case self._CHOOSE_DAY:
                return "Выберите день"
            case self._CHOOSE_LESSON:
                day = self.get_view_kwarg("_day", False)
                return f"{DAYS_OF_THE_WEEK[day.weekday() + 1].capitalize()} {day.strftime('%d.%m.%y')}\n\n" \
                    + "Выберите время"
            case self._CONFIRM:
                return await self._get_confirm_text()
            case _:
                raise RuntimeError("no default")

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((10000, 0), "Назад", {"_action": self._BACK})}
        match self._get_state():
            case self._CHOOSE_WEEK:
                lessons = self._get_all_free_lessons()
                for lesson in lessons:
                    monday = lesson.lesson_datetime - timedelta(days=lesson.lesson_datetime.weekday())
                    key = f"_week{monday.strftime('%y.%m.%d')}"
                    if key in res:
                        continue
                    res[key] = _ButtonStab(
                        (100 + monday.day + 100 * monday.month, 0),
                        f"{monday.strftime('%d.%m.%y')}-{(monday + timedelta(days=6)).strftime('%d.%m.%y')}",
                        {"_monday": monday, "_state": self._CHOOSE_DAY}
                    )
                return res
            case self._CHOOSE_DAY:
                monday = self.get_view_kwarg("_monday", False)
                lessons = self._get_free_lessons(monday, monday + timedelta(days=6))
                for lesson in lessons:
                    key = f"_weekday{lesson.lesson_datetime.weekday()}"
                    if key in res:
                        continue
                    res[key] = _ButtonStab(
                        (100 + lesson.lesson_datetime.weekday(), 0),
                        f"{DAYS_OF_THE_WEEK[lesson.lesson_datetime.weekday() + 1]}"
                        f" ({lesson.lesson_datetime.strftime('%d.%m.%y')})",
                        {"_day": to_midnight(lesson.lesson_datetime), "_state": self._CHOOSE_LESSON}
                    )
                return res
            case self._CHOOSE_LESSON:
                day = self.get_view_kwarg("_day", False)
                lessons = self._get_free_lessons(day, day + timedelta(hours=23, minutes=59))
                for lesson in lessons:
                    res[f"_lesson{lesson.lesson_datetime.isoformat()}"] = _ButtonStab(
                        (100 + 100 * lesson.lesson_datetime.hour + lesson.lesson_datetime.minute, 0),
                        f"{lesson.time_start}-{lesson.time_end}",
                        {"_datetime": lesson.lesson_datetime, "_state": self._CONFIRM}
                    )
                return res
            case self._CONFIRM:
                return {
                    "_yes": _ButtonStab(
                        (100, 0),
                        "Да",
                        kwargs={"_action": self._YES}
                    ),
                    "_no": _ButtonStab(
                        (100, 10),
                        "Нет",
                        kwargs={"_action": self._BACK}
                    )
                }
            case _:
                return res

    async def get_title(self) -> str:
        raise RuntimeError("No title")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case self._YES:
                await self._book_lesson()
                self.erase_view_kwargs()
                self.nav_context.tree_path.pop()
            case self._BACK:
                match self.get_view_kwarg("_state"):
                    case self._CONFIRM:
                        self.set_view_kwarg("_state", self._CHOOSE_LESSON)
                        self.get_view_kwarg("_datetime")
                    case self._CHOOSE_LESSON:
                        self.set_view_kwarg("_state", self._CHOOSE_DAY)
                        self.get_view_kwarg("_day")
                    case self._CHOOSE_DAY:
                        self.set_view_kwarg("_state", self._CHOOSE_WEEK)
                        self.get_view_kwarg("_week")
                    case _:
                        self.erase_view_kwargs()
                        self.nav_context.tree_path.pop()
        return self.nav_context

    def _get_state(self) -> str:
        return self.get_view_kwarg("_state", False)

    def _get_all_free_lessons(self) -> list[FreeLesson]:
        now = self._dt.now()
        return BookLessonsService.get_free_lessons_for(now, now + timedelta(days=31))

    def _get_free_lessons(self, start: datetime, end: datetime):
        now = self._dt.now()
        if start < now:
            start = now
        return BookLessonsService.get_free_lessons_for(start, end)

    @staticmethod
    def _week(monday: datetime) -> str:
        return f"{monday.strftime('%d.%m.%y')}-{(monday + timedelta(days=6)).strftime('%d.%m.%y')}"

    @abstractmethod
    async def _get_confirm_text(self):
        pass

    @abstractmethod
    async def _book_lesson(self):
        pass


@telegramupdate
class StudentBookLesson(_BookLessonBase):
    @inject
    def __init__(self, dt: DatetimeService, book: BookLessonsService, context: Context, users: UsersService):
        super().__init__(dt)
        self._users = users
        self._book = book
        self._context = context

    async def _book_lesson(self):
        user = self._context.authorized_user
        await self._users.send_menu_to_admins(
            [_TreeEntry(_AdminBookLessonConfirmation)],
            {"user_id": user.id, "datetime": self.get_view_kwarg("_datetime", False)})
        await self.tg_context.popup("Ок! Заявка на запись отправлена 👌")

    async def _get_confirm_text(self):
        dt = self.get_view_kwarg("_datetime", False)
        lesson = BookLessonsService.try_get_free_lesson(dt)
        return f"Записать на урок с {lesson.time_start} по {lesson.time_end} в " \
               f"{DAYS_OF_THE_WEEK[lesson.lesson_datetime.weekday() + 1]} {dt.strftime('%d.%m.%y')}?"

    @override
    def _get_state(self) -> str:
        state = super()._get_state()
        if not state:
            return self._CHOOSE_WEEK
        return state


@telegramupdate
class AdminBookLesson(_BookLessonBase):
    _CHOOSE_STUDENT = "student"

    @inject
    def __init__(self, dt: DatetimeService, users: UsersService, book: BookLessonsService):
        super().__init__(dt)
        self._book = book
        self._users = users

    @override
    async def get_message_text(self) -> str:
        match self._get_state():
            case self._CHOOSE_STUDENT:
                return "Выберите ученика"
            case _:
                return await super().get_message_text()

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = await super().get_view_buttons()
        match self._get_state():
            case self._CHOOSE_STUDENT:
                users = await self._users.get_all_regular_users_ordered()
                for i, user in enumerate(users):
                    res[f"_user{user.id}"] = _ButtonStab(
                        (100+i, 0),
                        user.fullname,
                        {"_user_id": user.id, "_state": self._CHOOSE_WEEK}
                    )
                return res
            case _:
                return res

    async def _get_confirm_text(self):
        dt = self.get_view_kwarg("_datetime", False)
        lesson = BookLessonsService.try_get_free_lesson(dt)
        user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id", False))
        return f"Поставить урок для {user.fullname} с {lesson.time_start} по {lesson.time_end} в " \
               f"{DAYS_OF_THE_WEEK[lesson.lesson_datetime.weekday() + 1]} {dt.strftime('%d.%m.%y')}?"

    async def _book_lesson(self):
        dt = self.get_view_kwarg("_datetime")
        user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id"))
        lesson = BookLessonsService.try_get_free_lesson(dt)
        if user and await self._book.book_lesson(user, dt):
            await self.tg_context.popup("Занятие успешно добавлено 👌")
            await self._users.send_text_message(
                user,
                f"Тук-тук 👀 Вас записали на занятие с {lesson.time_start} по {lesson.time_end} в "
                f"{DAYS_OF_THE_WEEK[lesson.lesson_datetime.weekday() + 1]} {lesson.lesson_datetime.strftime('%d.%m.%y')}")
        else:
            await self.tg_context.popup("Нельзя забронировать занятие 😥 Возможно, оно уже занято.")

    @override
    def _get_state(self) -> str:
        state = super()._get_state()
        if not state:
            return self._CHOOSE_STUDENT
        return state


@telegramupdate
class _AdminBookLessonConfirmation(BaseView):
    _CONFIRMED = "confirmed"
    _DECLINED = "declined"

    _YES = "yes"
    _NO = "no"

    @inject
    def __init__(self, users: UsersService, book: BookLessonsService, alarm: ErrorsMessenger):
        super().__init__()
        self._alarm = alarm
        self._book = book
        self._users = users

    async def get_message_text(self) -> str:
        match self.get_view_kwarg("_state", False):
            case self._CONFIRMED:
                return "Запись прошла успешно!"
            case self._DECLINED:
                return "Запись отменена, ученик получил уведомление."
            case _:
                user = await self._users.get_user_by_id(self.get_view_kwarg("user_id", False))
                free_lesson = BookLessonsService.try_get_free_lesson(self.get_view_kwarg("datetime", False))
                if not free_lesson:
                    await self._alarm.info_msg("не получилось найти free lesson, где-то ошибка")
                    return "Что-то пошло не так и ученик пытается записаться в занятое окно 🤔"
                dt = free_lesson.lesson_datetime
                return f"Ученик {user.fullname} хочет записаться на занятие " \
                       f"в {DAYS_OF_THE_WEEK[dt.weekday() + 1]} {dt.strftime('%d.%m.%y')} " \
                       f"с {free_lesson.time_start} по {free_lesson.time_end}\n\n" \
                       "Записываем?"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        if self.get_view_kwarg("_state", False):
            return {}
        return {
            "_yes": _ButtonStab((100, 0), "Записываем", {"_action": self._YES}),
            "_no": _ButtonStab((100, 10), "Нет", {"_action": self._NO})
        }

    async def get_title(self) -> str:
        raise RuntimeError("no title")

    async def handle(self) -> NavigationContext | None:
        user = await self._users.get_user_by_id(self.get_view_kwarg("user_id", False))
        free_lesson = BookLessonsService.try_get_free_lesson(self.get_view_kwarg("datetime", False))
        match self.get_view_kwarg("_action"):
            case self._YES:
                if await self._book.book_lesson(user, free_lesson.lesson_datetime):
                    await self.tg_context.popup(f"Ученик {user.fullname} успешно записан! 👌")
                    await self._send_confirm_to_user(user, free_lesson)
                    self.set_view_kwarg("_state", self._CONFIRMED)
                else:
                    await self.tg_context.popup("Не удалось записать ученика: место уже занято.")
                    self.set_view_kwarg("_state", self._DECLINED)
            case self._NO:
                await self._send_decline_to_user(user, free_lesson)
                self.set_view_kwarg("_state", self._DECLINED)
        return self.nav_context

    async def _send_confirm_to_user(self, user: User, lesson: FreeLesson):
        await self._users.send_text_message(
            user,
            f"Вы были успешно записаны на занятие {lesson.time_start} по {lesson.time_end} в "
            f"{DAYS_OF_THE_WEEK[lesson.lesson_datetime.weekday() + 1]} {lesson.lesson_datetime.strftime('%d.%m.%y')} 👌")

    async def _send_decline_to_user(self, user: User, lesson: FreeLesson):
        await self._users.send_text_message(
            user,
            f"Запись на занятие {lesson.time_start} по {lesson.time_end} в "
            f"{DAYS_OF_THE_WEEK[lesson.lesson_datetime.weekday() + 1]} {lesson.lesson_datetime.strftime('%d.%m.%y')} "
            f"не подтверждена 😢")
