from abc import ABC, abstractmethod
from datetime import timedelta, datetime

from injector import inject
from typing_extensions import override

from voice_bot.db.models import User
from voice_bot.domain.context import Context
from voice_bot.domain.services.book_lesson_service import FreeLesson, BookLessonsService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, to_midnight, dt_fmt_week, dt_fmt_rus, day_with_str_hours
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

    def __init__(self, dt: DatetimeService, book: BookLessonsService):
        super().__init__()
        self.book = book
        self._dt = dt

    async def get_message_text(self) -> str:
        match self._get_state():
            case self._CHOOSE_WEEK:
                return "Выберите неделю"
            case self._CHOOSE_DAY:
                return "Выберите день"
            case self._CHOOSE_LESSON:
                day = self.get_view_kwarg("_day", False)
                return f"{dt_fmt_rus(day)}\n\n" \
                    + "Выберите время"
            case self._CONFIRM:
                return await self._get_confirm_text()
            case _:
                raise RuntimeError("no default")

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((10000, 0), "Назад", {"_action": self._BACK})}
        match self._get_state():
            case self._CHOOSE_WEEK:
                monday = self._dt.dt_now_monday()
                for i in range(4):
                    key = f"_week{monday.strftime('%y.%m.%d')}"
                    res[key] = _ButtonStab(
                        (100 + monday.day + 100 * monday.month, 0),
                        dt_fmt_week(monday),
                        {"_monday": monday, "_state": self._CHOOSE_DAY}
                    )
                    monday += timedelta(days=7)
            case self._CHOOSE_DAY:
                monday = self.get_view_kwarg("_monday", False)
                now = self._dt.now()
                for i in range(7):
                    day = monday + timedelta(days=i)
                    if to_midnight(now) > day:
                        continue
                    key = f"_weekday{i}"
                    res[key] = _ButtonStab(
                        (100 + i, 0),
                        dt_fmt_rus(day),
                        {"_day": to_midnight(day), "_state": self._CHOOSE_LESSON}
                    )
            case self._CHOOSE_LESSON:
                day = self.get_view_kwarg("_day", False)
                lessons = await self.book.get_free_lessons(day)
                i = 0
                for key, lesson in sorted(lessons.items()):
                    res[f"_lesson{key}"] = _ButtonStab(
                        (100+i, 0),
                        f"{lesson.time_start}-{lesson.time_end}",
                        {"_datetime": day_with_str_hours(day, lesson.time_start), "_state": self._CONFIRM})
                    i += 1
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
        super().__init__(dt, book)
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
        lesson = await self._book.try_get_free_lesson(dt)
        return f"Записать на урок с {lesson.time_start} по {lesson.time_end} в {dt_fmt_rus(dt)}?"

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
        super().__init__(dt, book)
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
        lesson = await self.book.try_get_free_lesson(dt)
        user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id", False))
        return f"Поставить урок для {user.fullname} с {lesson.time_start} по {lesson.time_end} в " \
               f"{dt_fmt_rus(dt)}?"

    async def _book_lesson(self):
        dt = self.get_view_kwarg("_datetime")
        user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id"))
        lesson = await self.book.try_get_free_lesson(dt)
        if user and await self._book.book_lesson(user, dt):
            await self.tg_context.popup("Занятие успешно добавлено 👌")
            await self._users.send_text_message(
                user,
                f"Тук-тук 👀 Вас записали на занятие с {lesson.time_start} по {lesson.time_end} в "
                f"{dt_fmt_rus(dt)}")
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
                dt = self.get_view_kwarg("datetime", False)
                free_lesson = await self._book.try_get_free_lesson(dt)
                if not free_lesson:
                    await self._alarm.info_msg("не получилось найти free lesson, где-то ошибка")
                    return "Что-то пошло не так и ученик пытается записаться в занятое окно 🤔"
                return f"Ученик {user.fullname} хочет записаться на занятие " \
                       f"в {dt_fmt_rus(dt)} " \
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
        dt = self.get_view_kwarg("datetime", False)
        free_lesson = await self._book.try_get_free_lesson(dt)
        match self.get_view_kwarg("_action"):
            case self._YES:
                if await self._book.book_lesson(user, dt):
                    await self.tg_context.popup(f"Ученик {user.fullname} успешно записан! 👌")
                    await self._send_confirm_to_user(user, free_lesson, dt)
                    self.set_view_kwarg("_state", self._CONFIRMED)
                else:
                    await self.tg_context.popup("Не удалось записать ученика: место уже занято.")
                    self.set_view_kwarg("_state", self._DECLINED)
            case self._NO:
                await self._send_decline_to_user(user, free_lesson, dt)
                self.set_view_kwarg("_state", self._DECLINED)
        return self.nav_context

    async def _send_confirm_to_user(self, user: User, lesson: FreeLesson, dt: datetime):
        await self._users.send_text_message(
            user,
            f"Вы были успешно записаны на занятие {lesson.time_start} по {lesson.time_end} в {dt_fmt_rus(dt)} 👌")

    async def _send_decline_to_user(self, user: User, lesson: FreeLesson, dt: datetime):
        await self._users.send_text_message(
            user,
            f"Запись на занятие {lesson.time_start} по {lesson.time_end} в {dt_fmt_rus(dt)} не подтверждена 😢")
