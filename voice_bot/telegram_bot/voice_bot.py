import uuid

import structlog
from injector import singleton, inject, Injector
from structlog.contextvars import bound_contextvars
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from voice_bot.telegram_bot.commands import COMMANDS, CommandDefinition, CommandWithMenuDefinition
from voice_bot.telegram_bot.navigation.base_classes import NavigationContext
from voice_bot.telegram_bot.navigation.navigation import Navigation
from voice_bot.telegram_bot.navigation.navigation_command_handler import NavigationCommandHandler
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
        self._wire_callback_handler()

    def start_bot(self) -> None:
        self._application.run_polling()

    def _wire_commands(self) -> None:
        for name, cmd in COMMANDS.items():
            wrapper = _HandlerWrapper(name, cmd, self._injector, self._logger)
            self._application.add_handler(CommandHandler(name, wrapper.handle))

    def _wire_callback_handler(self) -> None:
        wrapper = _CallbackQueryHandlerWrapper(self._injector, self._logger)
        self._application.add_handler(CallbackQueryHandler(wrapper.handle))


class _HandlerWrapper:
    def __init__(self, cmd_name: str, cmd_def: CommandDefinition, injector: Injector, logger):
        self._logger = logger
        self._injector = injector
        self._cmd_name = cmd_name
        self._cmd_def = cmd_def

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with bound_contextvars(local_request_id=str(uuid.uuid4())):
            try:
                await self._logger.ainfo("Got update", telegram_update=update.to_json())
                for claim in self._cmd_def.claims:
                    if not await self._injector.get(claim, _TelegramUpdate).process(update, context):
                        return
                handler = self._injector.get(self._cmd_def.handler, _TelegramUpdate)
                if isinstance(self._cmd_def, CommandWithMenuDefinition) and isinstance(handler, NavigationCommandHandler):
                    handler.push_navigation_definition(NavigationContext(self._cmd_name, [], {}, {}),
                                                       self._cmd_def.navigation)
                await handler.handle(update, context)
            except Exception as e:
                await self._logger.aexception(e)
                raise


class _CallbackQueryHandlerWrapper:
    def __init__(self, injector: Injector, logger):
        self._logger = logger
        self._injector = injector

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with bound_contextvars(local_request_id=str(uuid.uuid4())):
            try:
                await self._logger.ainfo("Got callback update", telegram_update=update.to_json())
                nav_context = Navigation.parse_data(update.callback_query.data)
                menu_cmd_def = COMMANDS[nav_context.root_cmd]
                if not isinstance(menu_cmd_def, CommandWithMenuDefinition):
                    await update.callback_query.answer("Что-то пошло не так")
                    await self._logger.awarning("Callback query routed to command without navigation",
                                                cmd_name=nav_context.root_cmd)
                    return
                handler = self._injector.get(menu_cmd_def.handler, _TelegramUpdate)
                handler.push_navigation_definition(nav_context, menu_cmd_def.navigation)
                await handler.handle_callback(update, context)
            except Exception as e:
                await self._logger.aexception(e)
                raise
