from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class TextView(BaseView):
    async def get_title(self) -> str:
        raise NotImplementedError("Text view has no dynamic title")

    async def get_message_text(self) -> str:
        raise NotImplementedError("Text view has no dynamic message text")

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        if "is_root" in self.nav_context.context_vars:
            return {}

        return {
            "_back": _ButtonStab(
                (100, 0),
                "Назад",
                kwargs={"_back": "y"}
            )
        }

    async def handle(self) -> NavigationContext | None:
        if "_back" in self.nav_context.kwargs:
            self.nav_context.tree_path.pop()
            return self.nav_context
        return self.nav_context
