from voice_bot.telegram_bot.navigation.base_classes import BaseView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class Settings(BaseView):
    pass
