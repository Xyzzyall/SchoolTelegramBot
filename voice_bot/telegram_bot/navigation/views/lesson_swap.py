from datetime import timedelta, datetime

from injector import inject

from voice_bot.db.models import ScheduleRecord, FreeLesson
from voice_bot.domain.services.book_lesson_service import BookLessonsService
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import dt_fmt_rus, to_midnight, dt_fmt_week, to_day_end, \
    DatetimeService, day_with_str_hours
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class LessonSwapView(BaseView):
    CHOOSE_DAY = "day"
    CHOOSE_LESSON = "lesson"
    CONFIRM = "confirm"

    SWAP = "swap"
    BACK = "back"

    @inject
    def __init__(self, schedule: ScheduleService, book: BookLessonsService, users: UsersService, dt: DatetimeService):
        super().__init__()
        self.users = users
        self.dt = dt
        self.book = book
        self.schedule = schedule

    async def get_message_text(self) -> str:
        match self.get_view_kwarg("_state", False):
            case self.CONFIRM:
                lesson_id, _ = self.from_swap()
                swap_from = await self.schedule.get_lesson_by_id(lesson_id)
                swap_to, day = self.to_swap()
                if day:
                    free_lesson = await self.book.get_free_lesson_by_id(swap_to)
                    return f"Переставить урок ученика {swap_from.user.fullname} " \
                           f"(c {swap_from.time_start} по {swap_from.time_end}" \
                           f" в {dt_fmt_rus(swap_from.absolute_start_time)}) " \
                           f"в окно c {free_lesson.time_start} по {free_lesson.time_end} {dt_fmt_rus(day)}? 🤔"
                else:
                    lesson = await self.schedule.get_lesson_by_id(swap_to)
                    return f"Переставить уроки местами?\n\n" \
                           f"🥕 {swap_from.user.fullname} (c {swap_from.time_start} по {swap_from.time_end} " \
                           f"в {dt_fmt_rus(swap_from.absolute_start_time)})\n" \
                           f"🥕 {lesson.user.fullname} (c {lesson.time_start} по {lesson.time_end} " \
                           f"в {dt_fmt_rus(lesson.absolute_start_time)})\n"
            case self.CHOOSE_DAY:
                if self.from_swap():
                    return "Выбери день урока или окна с которым поменяться"
                else:
                    return "Выбери день урока, который нужно переместить"
            case self.CHOOSE_LESSON:
                if self.from_swap():
                    return "Выбери урок или окно с которым поменяться"
                else:
                    return "Выбери урок который нужно переместить"
            case self.CONFIRM:
                pass
            case _:
                if self.from_swap():
                    return "Выбери неделю урока или окна с которым поменяться"
                else:
                    return "Выбери неделю урока, который нужно переместить"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", {"_action": self.BACK})}
        match self.get_view_kwarg("_state", False):
            case self.CONFIRM:
                return {
                    "_yes": _ButtonStab((100, 0), "Да", {"_action": self.CONFIRM}),
                    "_back": _ButtonStab((100, 0), "Нет", {"_action": self.BACK})}
            case self.CHOOSE_DAY:
                if self.from_swap():
                    monday = self.get_view_kwarg("_week_to", False)
                    key = "_day_to"
                else:
                    monday = self.get_view_kwarg("_week_from", False)
                    key = "_day_from"

                today = to_midnight(self.dt.now())
                for i in range(7):
                    day = monday + timedelta(days=i)
                    if day >= today:
                        res[f"_day{i}"] = _ButtonStab(
                            (100+i, 0), dt_fmt_rus(day), {key: day, "_state": self.CHOOSE_LESSON})
            case self.CHOOSE_LESSON:
                if self.from_swap():
                    day = self.get_view_kwarg("_day_to", False)
                else:
                    day = self.get_view_kwarg("_day_from", False)
                lessons = await self.schedule.get_schedule(day, to_day_end(day))
                free_lessons = await self.book.get_free_lessons(day) if self.from_swap() else {}
                by_time_start = dict[str, ScheduleRecord | FreeLesson]()
                for lesson in lessons:
                    by_time_start[lesson.time_start] = lesson
                for key, val in free_lessons.items():
                    if key in by_time_start:
                        continue
                    by_time_start[key] = val

                kwarg_key = "_to_swap" if self.from_swap() else "_from_swap"
                to_state = self.CONFIRM if self.from_swap() else None
                i = 0
                for key, val in sorted(by_time_start.items()):
                    i += 1
                    if isinstance(val, ScheduleRecord):
                        res[f"_l{key}"] = _ButtonStab(
                            (100 + i, 0),
                            f"Занятие с {val.time_start} по {val.time_end}, {val.user.fullname}",
                            {kwarg_key: (val.id, None), "_state": to_state})
                    elif isinstance(val, FreeLesson):
                        res[f"_l{key}"] = _ButtonStab(
                            (100 + i, 0),
                            f"Окно с {val.time_start} по {val.time_end}",
                            {kwarg_key: (val.id, day), "_state": to_state})
                    else:
                        raise RuntimeError(f"Unexpected type of lesson {val.__class__}")
            case _:
                key = "_week_to" if self.from_swap() else "_week_from"
                monday = self.dt.dt_now_monday()
                for i in range(4):
                    res[f"_week{i}"] = _ButtonStab(
                        (100+i, 0), dt_fmt_week(monday), {key: monday, "_state": self.CHOOSE_DAY})
                    monday += timedelta(days=7)

        return res

    async def get_title(self) -> str:
        raise RuntimeError("not implemented")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case self.CONFIRM:
                lesson_id, _ = self.from_swap()
                from_swap = await self.schedule.get_lesson_by_id(lesson_id)
                to_swap, day = self.to_swap()

                if day:
                    user_msg = "Тук-тук \n\n"\
                               f"Твой урок c {from_swap.time_start} по {from_swap.time_end} " \
                               f"в {dt_fmt_rus(from_swap.absolute_start_time)} был перемещён!\n\n"
                    free_lesson = await self.book.get_free_lesson_by_id(to_swap, True)
                    if not free_lesson:
                        await self.tg_context.popup("Что-то переплелось и выбранное окно уже занято 😥")
                    else:
                        await self.schedule.move_lesson_to(from_swap, day_with_str_hours(day, free_lesson.time_start))
                        await self.tg_context.popup(f"Урок переставлен успешно!")
                        await self.users.send_text_message(
                            from_swap.user,
                            user_msg + f"Теперь он c {from_swap.time_start} по {from_swap.time_end} в "
                                       f"{dt_fmt_rus(from_swap.absolute_start_time)}!")

                else:
                    to_swap_lesson = await self.schedule.get_lesson_by_id(to_swap)
                    msg_from = self._swap_notice(from_swap, to_swap_lesson)
                    msg_to = self._swap_notice(to_swap_lesson, from_swap)
                    await self.schedule.swap_lessons(from_swap, to_swap_lesson)
                    await self.tg_context.popup(
                        f"Уроки с {from_swap.user.fullname} и с {to_swap_lesson.user.fullname} переставлены местами!")
                    await self.users.send_text_message(to_swap_lesson.user, msg_from)
                    await self.users.send_text_message(from_swap.user, msg_to)
                self.erase_view_kwargs()
                self.nav_context.tree_path.pop()
            case self.BACK:
                if self.from_swap():
                    match self.get_view_kwarg("_state", False):
                        case self.CONFIRM:
                            self.set_view_kwarg("_state", self.CHOOSE_LESSON)
                            self.to_swap(True)
                        case self.CHOOSE_LESSON:
                            self.set_view_kwarg("_state", self.CHOOSE_DAY)
                            self.get_view_kwarg("_date_to")
                        case self.CHOOSE_DAY:
                            self.set_view_kwarg("_state", None)
                            self.get_view_kwarg("_week_to")
                        case _:
                            self.from_swap(True)
                            self.set_view_kwarg("_state", self.CHOOSE_LESSON)
                else:
                    match self.get_view_kwarg("_state", False):
                        case self.CHOOSE_LESSON:
                            self.set_view_kwarg("_state", self.CHOOSE_DAY)
                            self.get_view_kwarg("_date_from")
                        case self.CHOOSE_DAY:
                            self.set_view_kwarg("_state", None)
                            self.get_view_kwarg("_week_from")
                        case _:
                            self.erase_view_kwargs()
                            self.nav_context.tree_path.pop()
        return self.nav_context

    @staticmethod
    def _swap_notice(from_swap, to_swap_lesson):
        return f"Тук-тук 👀\n\n" \
               f"Твой урок c {from_swap.time_start} по {from_swap.time_end} " \
               f"в {dt_fmt_rus(from_swap.absolute_start_time)} был перемещён!\n\n" \
               f"Теперь он c {to_swap_lesson.time_start} по {to_swap_lesson.time_end} в " \
               f"{dt_fmt_rus(to_swap_lesson.absolute_start_time)}!"

    def from_swap(self, pop: bool = False) -> int | None:
        return self.get_view_kwarg("_from_swap", pop)

    def to_swap(self, pop: bool = False) -> int | None:
        return self.get_view_kwarg("_to_swap", pop)


