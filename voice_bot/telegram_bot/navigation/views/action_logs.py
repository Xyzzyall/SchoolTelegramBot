from datetime import timedelta

from injector import inject

from voice_bot.domain.services.actions_logger import ActionsLoggerService, SUBSCRIPTIONS
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, dt_fmt
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class ActionLogsView(BaseView):
    _BACK_LOOKUP = timedelta(days=90)

    _LOG_FOR_USER = "for_user"
    _SUBS_TO_ADD = "add_sub"

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
            case self._LOG_FOR_USER:
                res: list[str] = []
                user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                subs = await self._log.count_subscriptions_on_date(user, self._dt.now())
                for sub in subs:
                    if sub.is_stub:
                        continue
                    res.append(f"*Абонемент с {dt_fmt(sub.valid_from)} по {dt_fmt(sub.valid_to)}*")
                    res.append(f"- уроков прошло: {sub.counted_lessons} из {sub.lessons}")
                    res.append(f"- отмен: {sub.counted_cancellations} из {sub.cancellations}")
                    res.append("")
                for sub in subs:
                    if sub.is_stub and (sub.counted_cancellations > 0 or sub.cancellations > 0):
                        res.append("*Неучтенные уроки и отмены (не попавшие ни в один абонемент):*")
                        if sub.counted_lessons > 0:
                            res.append(f"- {sub.counted_lessons} уроков")
                        if sub.counted_cancellations > 0:
                            res.append(f"- {sub.counted_cancellations} отмен")
                        res.append("")
                        break

                return "\n".join(res) if res else "У ученика нет абонементов и неучтённых занятий и отмен!"
            case self._SUBS_TO_ADD:
                return "Какой абонемент добавить?"
            case _:
                return "Выбери ученика"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", {"_action": self._BACK})}
        match self.get_view_kwarg("_state", False):
            case self._SUBS_TO_ADD:
                for i, sub in enumerate(SUBSCRIPTIONS):
                    res[f"_sub{i}"] = _ButtonStab((100 + i, 0), str(sub), {"_action": self._ADD_SUB, "_sub": sub})
            case self._LOG_FOR_USER:
                res["_add_sub"] = _ButtonStab((100, 0), "Добавить абонемент", {"_state": self._SUBS_TO_ADD})
            case _:
                users = await self._users.get_all_regular_users()
                for i, user in enumerate(users):
                    res[f"_u{user.id}"] = _ButtonStab(
                        (100 + i, 0),
                        user.fullname,
                        {"_state": self._LOG_FOR_USER, "_user_id": user.id}
                    )
        return res

    async def get_title(self) -> str:
        raise RuntimeError("no title")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case self._ADD_SUB:
                sub = self.get_view_kwarg("_sub")
                user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id", False))
                await self._log.log_subscription(user, sub, self._dt.now())
                await self.tg_context.popup("Абонемент успешно добавлен! 👌")
                if sub.lessons > 1:
                    await self._users.send_text_message(
                        user,
                        f"Привет! Тебе добавлен абонемент на {sub.lessons} занятий 🤞"
                    )
                self.set_view_kwarg("_state", self._LOG_FOR_USER)
            case self._BACK:
                match self.get_view_kwarg("_state", False):
                    case self._SUBS_TO_ADD:
                        self.set_view_kwarg("_state", self._LOG_FOR_USER)
                    case self._LOG_FOR_USER:
                        self.set_view_kwarg("_state", None)
                    case _:
                        self.erase_view_kwargs()
                        self.nav_context.tree_path.pop()
        return self.nav_context
