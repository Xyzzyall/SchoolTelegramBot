import traceback

from injector import singleton, inject

from voice_bot.telegram_bot.telegram_bot_proxy import TelegramBotProxy


@singleton
class ErrorsMessenger:
    _MY_CHAT_ID = "242173251"

    @inject
    def __init__(self, tg: TelegramBotProxy):
        self._tg = tg

    async def alarm(self, e: Exception):
        msg = "у нас ошибка месье\n\n```" + '\n'.join(traceback.format_exception(e, limit=1)) + '```'
        await self._tg.bot.send_message(
            self._MY_CHAT_ID,
            msg,
            parse_mode="Markdown"
        )

    async def info_msg(self, msg: str):
        await self._tg.bot.send_message(
            self._MY_CHAT_ID,
            msg,
            parse_mode="Markdown"
        )
