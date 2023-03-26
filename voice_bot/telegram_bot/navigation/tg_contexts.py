from dataclasses import dataclass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from voice_bot.telegram_bot.navigation.base_classes import TgContext
from voice_bot.telegram_bot.telegram_bot_proxy import TelegramBotProxy


class UpdateContext(TgContext):
    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.update = update
        self.context = context
        self._chat_id = str(update.effective_user.id)

    def get_chat_id(self) -> str:
        return self._chat_id

    async def popup(self, text: str):
        if not self.update.callback_query:
            return
        await self.update.callback_query.answer(text)

    async def message(self, text: str, buttons: list[list[InlineKeyboardButton]]):
        if not self.update.effective_message:
            return
        await self.update.effective_message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown"
        )


@dataclass
class ProxyContext(TgContext):
    proxy: TelegramBotProxy
    chat_id: str

    def get_chat_id(self) -> str:
        return self.chat_id

    async def popup(self, text: str):
        # no callback context, therefore cannot answer to it
        pass

    async def message(self, text: str, buttons: list[list[InlineKeyboardButton]]):
        await self.proxy.bot.send_message(
            self.chat_id, text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
