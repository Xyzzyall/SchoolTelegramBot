from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class NextLesson(TextView):
    async def get_title(self) -> str:
        raise RuntimeError("NextLesson is supposed to have title override")

    async def get_message_text(self) -> str:
        pass
