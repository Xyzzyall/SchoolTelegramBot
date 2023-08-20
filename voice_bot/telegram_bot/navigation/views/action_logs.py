from datetime import timedelta

from injector import inject

from voice_bot.domain.services.actions_logger import ActionsLoggerService, SUBSCRIPTIONS, Subscription
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, dt_fmt, str_timedelta_days, dt_fmt_rus
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class ActionLogsView(BaseView):
    _BACK_LOOKUP = timedelta(days=90)

    _BACK = "back"
    _ADD_SUB = "add_sub"

    @inject
    def __init__(self, users: UsersService, log: ActionsLoggerService, dt: DatetimeService):
        super().__init__()
        self._dt = dt
        self._log = log
        self._users = users

    async def get_message_text(self) -> str:
        match self.get_view_kwarg("_state", False):
            case "confirm":
                user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                sub = self.get_view_kwarg("_sub", False)
                log_day = self.get_view_kwarg("_log_day", False)
                return f"Создаем абонемент для {user.fullname} на {sub.lessons} занятий " \
                       f"с {dt_fmt(log_day)} по {dt_fmt(log_day + sub.timespan)}? 👀"
            case "for_user":
                res: list[str] = []
                user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                subs = await self._log.count_subscriptions_on_date(user, self._dt.now())
                stub_sub: Subscription = None
                for sub in subs:
                    if sub.is_stub:
                        stub_sub = sub
                        continue
                    res.append(f"*Абонемент с {dt_fmt(sub.valid_from)} по {dt_fmt(sub.valid_to)}*")
                    res.append(f"- уроков прошло: {sub.counted_lessons} из {sub.lessons}")
                    res.append(f"- отмен: {sub.counted_cancellations} из {sub.cancellations}")
                    res.append("")

                if not stub_sub:
                    raise RuntimeError("stub sub is not found")

                if stub_sub.counted_lessons == 0 and stub_sub.counted_cancellations == 0:
                    res.append("У ученика нет неучтенных уроков и отмен.")
                else:
                    res.append(f"Не учтено *{stub_sub.counted_lessons}* уроков, их даты:")
                    for dt in stub_sub.lesson_dates:
                        res.append(f"- урок {dt_fmt(dt)}")
                    res.append("")
                    res.append(f"Не учтено *{stub_sub.counted_cancellations}* отмен.")

                return "\n".join(res) if res else "У ученика нет абонементов и неучтённых занятий и отмен!"
            case "add_sub":
                return "Какой абонемент добавить?"
            case "sub_date":
                return "С какой даты включить абонемент?"
            case _:
                return "Выбери ученика"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", {"_action": "back"})}
        match self.get_view_kwarg("_state", False):
            case "confirm":
                return {
                    "_yes": _ButtonStab((100, 0), "Создать", {"_action": "add_sub"}),
                    "_no": _ButtonStab((100, 10), "Назад", {"_action": "back"})
                }
            case "sub_date":
                now = self._dt.now()
                for i in range(-14, 15):
                    day = now + timedelta(days=i)
                    res[f"_subdate{i}"] = _ButtonStab(
                        (100+i, 0),
                        str_timedelta_days(i, day),
                        {"_state": "confirm", "_log_day": day}
                    )
            case "add_sub":
                for i, sub in enumerate(SUBSCRIPTIONS):
                    res[f"_sub{i}"] = _ButtonStab((100 + i, 0), str(sub), {"_state": "sub_date", "_sub": sub})
            case "for_user":
                res["_add_sub"] = _ButtonStab((100, 0), "Добавить абонемент", {"_state": "add_sub"})
            case _:
                users = await self._users.get_all_regular_users()
                for i, user in enumerate(users):
                    res[f"_u{user.id}"] = _ButtonStab(
                        (100 + i, 0),
                        user.fullname,
                        {"_state": "for_user", "_user_id": user.id}
                    )
        return res

    async def get_title(self) -> str:
        raise RuntimeError("no title")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case "add_sub":
                sub = self.get_view_kwarg("_sub")
                user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id"))
                on_day = self.get_view_kwarg("_log_day")
                new_sub = await self._log.log_subscription(user, sub, on_day)
                await self.tg_context.popup("Абонемент успешно добавлен! 👌")
                await self._users.send_text_message_to_admins(
                    f"Был добавлен абонемент ученику {user.fullname} с "
                    f"{dt_fmt_rus(new_sub.subs_valid_from)} по {dt_fmt_rus(new_sub.subs_valid_to)} "
                    f"на {new_sub.subs_quantity} уроков и {new_sub.subs_cancellations} отмен")

                if sub.lessons > 1:
                    await self._users.send_text_message(
                        user,
                        f"Привет! Тебе добавлен абонемент на {sub.lessons} занятий 🤞"
                    )
                self.erase_view_kwargs()
                self.nav_context.tree_path.pop()
            case "back":
                match self.get_view_kwarg("_state", False):
                    case "confirm":
                        self.get_view_kwarg("_log_date")
                        self.set_view_kwarg("_state", "sub_date")
                    case "sub_date":
                        self.get_view_kwarg("_sub")
                        self.set_view_kwarg("_state", "add_sub")
                    case "add_sub":
                        self.set_view_kwarg("_state", "for_user")
                    case "for_user":
                        self.set_view_kwarg("_state", None)
                    case _:
                        self.erase_view_kwargs()
                        self.nav_context.tree_path.pop()
        return self.nav_context
