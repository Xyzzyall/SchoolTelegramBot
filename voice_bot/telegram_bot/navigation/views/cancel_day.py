from datetime import datetime, timedelta

from injector import inject

from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, dt_fmt_rus, dt_fmt_week
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CancelDayView(BaseView):
    @inject
    def __init__(self, schedule: ScheduleService, users: UsersService, dt: DatetimeService):
        super().__init__()
        self.dt = dt
        self.users = users
        self.schedule = schedule

    async def get_message_text(self) -> str:
        match self.get_view_kwarg("_state", False):
            case "confirm":
                on_day: datetime = self.get_view_kwarg("_on_day", False)
                lessons = await self.schedule.get_schedule_for_day(on_day)

                if not lessons:
                    return f"Нет занятий для отмены на {dt_fmt_rus(on_day)}!"

                txt = [f"Подверди отмену всех занятий на {dt_fmt_rus(on_day)}.\n\n"
                       f"Список уроков, которые будут отменены ({len(lessons)} уроков):"]
                for lesson in lessons:
                    txt.append(f" - c {lesson.time_start} по {lesson.time_end}, {lesson.user.fullname}")
                return "\n".join(txt)
            case "weekday":
                return "Выбери день недели"
            case _:
                return "Отмена всех занятий в день. Выбери неделю."

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", kwargs={"_action": "back"})}

        match self.get_view_kwarg("_state", False):
            case "confirm":
                return {
                    "_no": _ButtonStab((100, 0), "Назад", kwargs={"_action": "back"}),
                    "_yes": _ButtonStab((100, 10), "Отменить", kwargs={"_action": "cancel"})}
            case "weekday":
                current_day: datetime = self.get_view_kwarg("_on_week", False)
                now = self.dt.now()
                for i in range(7):
                    if now < current_day:
                        res[f"_day{i}"] = _ButtonStab(
                            (100 + i, 0),
                            dt_fmt_rus(current_day),
                            kwargs={"_state": "confirm", "_on_day": current_day})

                    current_day += timedelta(days=1)
            case _:
                monday = self.dt.dt_now_monday()
                for i in range(4):
                    res[f"_week{i}"] = _ButtonStab(
                        (100 + i, 0),
                        dt_fmt_week(monday),
                        kwargs={"_state": "weekday", "_on_week": monday})
                    monday += timedelta(days=7)

        return res

    async def get_title(self) -> str:
        raise RuntimeError("not implemented")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case "cancel":
                on_day: datetime = self.get_view_kwarg("_on_day")
                if await self.schedule.cancel_lessons_on_day(on_day):
                    await self.tg_context.popup("Уроки успешно отменены")
                else:
                    await self.tg_context.popup("Нет уроков для отмены")
                self.close()
            case "back":
                match self.get_view_kwarg("_state", False):
                    case "confirm":
                        self.set_view_kwarg("_state", "weekday")
                        self.get_view_kwarg("_on_day")
                    case "weekday":
                        self.get_view_kwarg("_state")
                        self.get_view_kwarg("_on_week")
                    case _:
                        self.close()

        return self.nav_context


