from datetime import timedelta

from injector import inject

from voice_bot.db.enums import UserActionType
from voice_bot.domain.services.actions_logger import ActionsLoggerService, Subscription
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, dt_fmt, dt_fmt_time, dt_fmt_week, dt_fmt_rus
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class ActionsEditorView(BaseView):
    @inject
    def __init__(self, actions: ActionsLoggerService, dt: DatetimeService, users: UsersService):
        super().__init__()
        self.users = users
        self.dt = dt
        self.actions = actions

    async def get_message_text(self) -> str:
        match self.get_view_kwarg("_state", False):
            case "confirm":
                user = await self.users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                day = self.get_view_kwarg("_day", False)
                return f"Добавить ученику {user.fullname} занятие в {dt_fmt(day)}?"
            case "days":
                user = await self.users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                return f"Ученик {user.fullname}. выбери день в который было занятие"
            case "weeks":
                user = await self.users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                return f"Ученик {user.fullname}. выбери неделю в которую было занятие"
            case "user":
                res: list[str] = []
                user = await self.users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                user_name = f"Ученик {user.fullname}, уроки и отмены за последние 3 месяца:\n\n"
                now = self.dt.now()
                subs = await self.actions.count_subscriptions_on_date(user, now)
                stub_sub: Subscription | None = None
                for sub in subs:
                    if sub.is_stub:
                        stub_sub = sub
                        continue

                    res.append(f"🎃 Абонемент с {dt_fmt(sub.valid_from)} по {dt_fmt(sub.valid_to)} "
                               f"на {sub.lessons} занятий")
                    if sub.counted_lessons:
                        res.append("Уроки:")
                        for lesson in sub.lesson_dates:
                            res.append(f"  🥕 {dt_fmt_time(lesson)}")
                    if sub.counted_cancellations:
                        res.append("Отмены:")
                        for cancellation in sub.cancellation_dates:
                            res.append(f"  🥕 {dt_fmt_time(cancellation)}")
                    res.append("")

                if stub_sub.counted_lessons:
                    res.append("")
                    res.append(f"💩 Неучтенные занятия:")
                    for lesson in stub_sub.lesson_dates:
                        res.append(f"  🥕 {dt_fmt_time(lesson)}")

                if stub_sub.counted_cancellations:
                    res.append("")
                    res.append("💩 Неучтенные отмены:")
                    for cancellation in stub_sub.cancellation_dates:
                        res.append(f"  🥕 {dt_fmt_time(cancellation)}")

                return user_name + (
                    "\n".join(res) if res else "У ученика нет занятий и отмен.")
            case _:
                return "Добавить неучтенный урок. Выбери ученика"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", {"_action": "back"})}
        match self.get_view_kwarg("_state", False):
            case "confirm":
                return {
                    "_yes": _ButtonStab((100, 0), "Добавить урок", {"_action": "log"}),
                    "_no": _ButtonStab((100, 10), "Назад", {"_action": "back"})
                }
            case "days":
                now = self.dt.now()
                day = self.get_view_kwarg("_monday", False)
                for i in range(7):
                    if day > now:
                        break
                    res[f"_day{i}"] = _ButtonStab(
                        (100 + i, 0),
                        dt_fmt_rus(day),
                        {"_state": "confirm", "_day": day}
                    )
                    day += timedelta(days=1)
            case "weeks":
                monday = self.dt.dt_now_monday()
                for i in range(12):
                    res[f"_week{i}"] = _ButtonStab(
                        (120 - i, 0),
                        dt_fmt_week(monday),
                        {"_state": "days", "_monday": monday}
                    )
                    monday -= timedelta(days=7)
            case "user":
                res["_add_lesson"] = _ButtonStab((100, 0), "Добавить урок", {"_state": "weeks"})
            case _:
                users_list = await self.users.get_all_regular_users()
                for i, user in enumerate(users_list):
                    res[f"_u{user.id}"] = _ButtonStab(
                        (100 + i, 0),
                        user.fullname,
                        {"_state": "user", "_user_id": user.id}
                    )
        return res

    async def get_title(self) -> str:
        raise RuntimeError("not implemented")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case "log":
                user = await self.users.get_user_by_id(self.get_view_kwarg("_user_id"))
                day = self.get_view_kwarg("_day")
                await self.actions.log_lesson(user, day)
                await self.tg_context.popup(f"Ученику {user.fullname} был успешно добавлен урок в {dt_fmt_rus(day)} 👌")
                self.erase_view_kwargs()
                self.nav_context.tree_path.pop()
            case "back":
                match self.get_view_kwarg("_state", False):
                    case "confirm":
                        self.get_view_kwarg("_day")
                        self.set_view_kwarg("_state", "days")
                    case "days":
                        self.get_view_kwarg("_monday")
                        self.set_view_kwarg("_state", "weeks")
                    case "weeks":
                        self.set_view_kwarg("_state", "user")
                    case "user":
                        self.get_view_kwarg("_user_id")
                        self.set_view_kwarg("_state", None)
                    case _:
                        self.erase_view_kwargs()
                        self.nav_context.tree_path.pop()
        return self.nav_context
