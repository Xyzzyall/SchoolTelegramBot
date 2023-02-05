from injector import singleton
from telegram.ext import ExtBot


@singleton
class TelegramBotProxy:
    bot: ExtBot = None

    def push_bot(self, bot: ExtBot):
        self.bot = bot
