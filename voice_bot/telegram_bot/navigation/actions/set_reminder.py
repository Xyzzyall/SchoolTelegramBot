from voice_bot.telegram_bot.navigation.base_classes import BaseAction
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class SetReminder(BaseAction):
    pass
