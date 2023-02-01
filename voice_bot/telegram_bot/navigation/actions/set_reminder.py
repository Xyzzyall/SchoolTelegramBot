from voice_bot.telegram_bot.navigation.base_classes import BaseAction
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class SetReminder(BaseAction):
    async def handle_action(self):
        pass

    async def get_title(self) -> str:
        return f"❌ {self.nav_context.context_vars['title']}"
