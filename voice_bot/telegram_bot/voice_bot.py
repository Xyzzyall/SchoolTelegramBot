import uuid

import structlog
from injector import singleton, inject, Injector
from structlog.contextvars import bound_contextvars
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.commands import _COMMANDS
from voice_bot.telegram_di_scope import _TelegramUpdate
from voice_bot.voice_bot_configurator import VoiceBotConfigurator


@singleton
class VoiceBot:
    @inject
    def __init__(self, configuration: VoiceBotConfigurator, injector: Injector):
        self._logger = structlog.get_logger(class_name=__class__.__name__)
        self._telegram_token = configuration.telegram_bot_token
        self._injector = injector
        self._application = Application.builder().token(self._telegram_token).build()
        self._wire_commands()

    def start_bot(self) -> None:
        self._application.run_polling()

    def _wire_commands(self) -> None:
        for cmd in _COMMANDS:
            wrapper = _HandlerWrapper(cmd.handler, self._injector, self._logger)
            self._application.add_handler(CommandHandler(cmd.command_nade, wrapper.handle))


class _HandlerWrapper:
    def __init__(self, target_handler: type[BaseUpdateHandler], injector: Injector, logger):
        self._logger = logger
        self._target_handler = target_handler
        self._injector = injector

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with bound_contextvars(local_request_id=str(uuid.uuid4())):
            await self._logger.ainfo("Got update", telegram_update=update.to_json())
            handler = self._injector.get(self._target_handler, _TelegramUpdate)
            await handler.handle(update, context)



