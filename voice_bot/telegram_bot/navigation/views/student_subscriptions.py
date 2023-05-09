from injector import inject

from voice_bot.domain.context import Context
from voice_bot.domain.services.actions_logger import ActionsLoggerService
from voice_bot.misc.datetime_service import DatetimeService, dt_fmt
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class StudentSubscriptions(TextView):
    @inject
    def __init__(self, log: ActionsLoggerService, dt: DatetimeService, context: Context):
        super().__init__()
        self._user = context.authorized_user
        self._dt = dt
        self._log = log

    async def get_message_text(self) -> str:
        now = self._dt.now()
        subs = await self._log.count_subscriptions_on_date(self._user, now)
        res = []
        for sub in subs:
            if sub.is_stub or not sub.is_valid(now):
                continue
            res.append(f"*Абонемент с {dt_fmt(sub.valid_from)} по {dt_fmt(sub.valid_to)}*")
            res.append(f"- уроков прошло: {sub.counted_lessons} из {sub.lessons}")
            res.append(f"- отмен: {sub.counted_cancellations} из {sub.cancellations}")
            res.append("")

        if not res:
            return "Не удалось найти действующих абонементов 🤔\n\n" \
                   "Либо у тебя действительно их нет, либо их еще не успели добавить."
        return "\n".join(res)
