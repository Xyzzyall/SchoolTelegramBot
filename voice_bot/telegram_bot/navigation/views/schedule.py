from voice_bot.telegram_bot.navigation.base_classes import BaseRootView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class Schedule(BaseRootView):
    async def get_message_text(self) -> str:
        raise RuntimeError("ScheduleService is supposed to have template override")

