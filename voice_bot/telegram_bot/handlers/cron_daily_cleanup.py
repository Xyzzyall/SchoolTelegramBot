from injector import inject
from telegram.ext import ContextTypes

from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_bot.navigation.misc.callback_data_codec import CallbackDataCodec
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CronDailyCleanup(BaseScheduleHandler):
    @inject
    def __init__(self, callback_codec: CallbackDataCodec):
        self._callback_codec = callback_codec

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        self._callback_codec.clear_old()
