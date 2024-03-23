from voice_bot.telegram_bot.navigation.base_classes import BaseView, _ButtonStab, NavigationContext
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class EmptySubsView(BaseView):
    async def get_title(self) -> str:
        raise RuntimeError()

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        pass

    async def get_message_text(self) -> str:
        pass

    async def handle(self) -> NavigationContext | None:
        pass

