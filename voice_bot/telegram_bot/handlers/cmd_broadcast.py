from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.services.message_builder import MessageBuilder
from voice_bot.services.users_service import UsersService
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdBroadcast(BaseUpdateHandler):
    @inject
    def __init__(self, users: UsersService):
        self._users = users

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users = await self._users.get_authorized_users()

        message_text = update.effective_message.text
        new_line_index = message_text.find("\n")

        if new_line_index == -1:
            await update.effective_message.reply_text(
                "Для проведения рассылки введите сообщение с новой строки\n\nнапример:\n"
                "_/broadcast\nСообщение для рассылки_",
                parse_mode='Markdown'
            )
            return

        message_text = message_text[new_line_index+1:]

        for user in users:
            await self._users.send_message(user, message_text)

        await update.effective_message.reply_text(
            f"Сообщение было отправлено {len(users)} пользователям."
        )

