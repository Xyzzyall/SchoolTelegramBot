import asyncio
import random
from datetime import timedelta

from injector import inject

from voice_bot.domain.services.actions_logger import ActionsLoggerService, SUBSCRIPTIONS, Subscription, \
    SubscriptionTemplate
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

                mult = self.get_view_kwarg("_mult", False) or 1
                sub_template: SubscriptionTemplate = self.get_view_kwarg("_sub", False)
                sub_template = sub_template.multiply(mult)

                log_day_delta = self.get_view_kwarg("_log_day_delta", False) or 0
                log_day = self._dt.now() + timedelta(days=log_day_delta)

                mult_text = "" if mult == 1 else f"🐈 абонемент х{mult}\n"
                log_day_text = "" if log_day_delta == 0 else f"🐈 дата смещена на {log_day_delta} дней"

                return f"Создаем абонемент для {user.fullname} на {sub_template.lessons} занятий " \
                       f"с {dt_fmt(log_day)} по {dt_fmt(log_day + sub_template.timespan)}? 👀\n\n" \
                       + mult_text + log_day_text
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
            case _:
                return "Выбери ученика"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", {"_action": "back"})}
        match self.get_view_kwarg("_state", False):
            case "confirm":
                return {
                    "_yes": _ButtonStab((100, 0), "Создать", {"_action": "add_sub"}),
                    "_blank0": _ButtonStab((110, 0), "🐈 сложить абонемент 🐈", {"_action": "meow"}),
                    "_increase": _ButtonStab((120, 0), "Сложить", kwargs={"_action": "increase"}),
                    "_decrease": _ButtonStab((120, 10), "Вычесть", kwargs={"_action": "decrease"}),
                    "_blank1": _ButtonStab((130, 0), "🐈 сместить дату на дни 🐈", {"_action": "meow"}),
                    "_date-7": _ButtonStab((140, 0), "-7", kwargs={"_action": "day_delta", "_days": -7}),
                    "_date-3": _ButtonStab((140, 1), "-3", kwargs={"_action": "day_delta", "_days": -3}),
                    "_date-1": _ButtonStab((140, 2), "-1", kwargs={"_action": "day_delta", "_days": -1}),
                    "_date0": _ButtonStab((140, 3), "🪃", kwargs={"_action": "day_delta", "_days": 0}),
                    "_date+1": _ButtonStab((140, 4), "+1", kwargs={"_action": "day_delta", "_days": 1}),
                    "_date+3": _ButtonStab((140, 5), "+3", kwargs={"_action": "day_delta", "_days": 3}),
                    "_date+7": _ButtonStab((140, 6), "+7", kwargs={"_action": "day_delta", "_days": 7}),
                    "_blank2": _ButtonStab((160, 0), "🐈🐈‍⬛🐈🐈‍⬛🐈🐈‍⬛", {"_action": "meow"}),
                    "_no": _ButtonStab((200, 0), "Назад", {"_action": "back"}),
                }
            case "add_sub":
                for i, sub in enumerate(SUBSCRIPTIONS):
                    res[f"_sub{i}"] = _ButtonStab((100 + i, 0), str(sub), {"_state": "confirm", "_sub": sub})
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
                sub_template: SubscriptionTemplate = self.get_view_kwarg("_sub")
                sub_template = sub_template.multiply(self.get_view_kwarg("_mult") or 1)

                user = await self._users.get_user_by_id(self.get_view_kwarg("_user_id"))

                log_day_delta = self.get_view_kwarg("_log_day_delta") or 0
                on_day = self._dt.now() + timedelta(days=log_day_delta)

                new_sub = await self._log.log_subscription(user, sub_template, on_day)

                await self.tg_context.popup("Абонемент успешно добавлен! 👌")
                await self._users.send_text_message_to_admins(
                    f"Был добавлен абонемент ученику {user.fullname} с "
                    f"{dt_fmt(new_sub.subs_valid_from)} по {dt_fmt(new_sub.subs_valid_to)} "
                    f"на {new_sub.subs_quantity} уроков и {new_sub.subs_cancellations} отмен")

                await self._users.send_text_message(
                    user,
                    f"Привет! Тебе добавлен абонемент на {new_sub.subs_quantity} занятий 🤞\n\n"
                    f"Он будет действовать с {dt_fmt(new_sub.subs_valid_from)} "
                    f"по {dt_fmt(new_sub.subs_valid_to)} 🗓️"
                )
                self.erase_view_kwargs()
                self.nav_context.tree_path.pop()
            case "increase":
                mult = self.get_view_kwarg("_mult", False) or 1
                if mult >= 3:
                    await self.tg_context.popup("Абик уже утроен, успокой свою жадность 😈")
                else:
                    self.set_view_kwarg("_mult", mult + 1)
                    await self.tg_context.popup("💃" * mult)
            case "decrease":
                mult = self.get_view_kwarg("_mult", False) or 1
                if mult <= 1:
                    await self.tg_context.popup("Дальше вычитать нельзя 😶")
                else:
                    self.set_view_kwarg("_mult", mult - 1)
                    await self.tg_context.popup("💃" * mult)
            case "day_delta":
                delta = self.get_view_kwarg("_log_day_delta", False) or 0
                days = self.get_view_kwarg("_days")
                if days == 0:
                    self.set_view_kwarg("_log_day_delta", 0)
                else:
                    if abs(delta + days) > 120:
                        await self.tg_context.popup("Не наступай так легкомысленно на грани будущего и прошлого 🚬🦍")
                    else:
                        self.set_view_kwarg("_log_day_delta", delta + days)
                        await self.tg_context.popup("✏️🗓️")
            case "meow":
                await self.tg_context.popup("😺 мяу")
                if random.randint(0, 6) == 5:
                    await self.tg_context.message("🎇🎈🎃🎊✨ **МУЯЯЯЯУУУУУ** 🎇🎈🎃🎊✨", [])
                    await asyncio.sleep(3)
                    await self.tg_context.message("**ТЫ РАЗБУДИЛ КОШАЧЬЕГО БОГА** 🙀🙀🙀🙀", [])
                    await asyncio.sleep(3)
                    await self.tg_context.message("**ЧТОБЫ ОТМЕНИТЬ ПОРЧУ НА ПОНОС** 💩💩💩😱", [])
                    await asyncio.sleep(3)
                    await self.tg_context.message("**СРОЧНО ПОГЛАДЬ БЛИЖАЙШЕГО КОТА** 🐈🐈‍⬛🐈🐈‍⬛🐈🐈‍⬛", [])
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
