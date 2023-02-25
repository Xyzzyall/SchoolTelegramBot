from injector import inject

from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.telegram_bot.navigation.base_classes import BaseRootView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class Settings(BaseRootView):
    @inject
    def __init__(self, msg_builder: MessageBuilder):
        self._msg_builder = msg_builder

    async def get_message_text(self) -> str:
        return await self._msg_builder.format("Настройки")
