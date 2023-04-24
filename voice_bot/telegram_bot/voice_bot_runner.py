import json
import uuid
from datetime import timedelta, datetime

import structlog
from injector import singleton, inject, Injector
from structlog.contextvars import bound_contextvars
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

from voice_bot.misc.stopwatch import Stopwatch
from voice_bot.telegram_bot.commands import COMMANDS, CommandDefinition, CommandWithMenuDefinition
from voice_bot.telegram_bot.cron_jobs import CronJob, CRON_JOBS
from voice_bot.telegram_bot.handlers.navigation_command_handler import NavigationCommandHandler
from voice_bot.telegram_bot.handlers.text_message_handler import TextMessageHandler
from voice_bot.telegram_bot.services.errors_messenger import ErrorsMessenger
from voice_bot.telegram_bot.telegram_bot_proxy import TelegramBotProxy
from voice_bot.telegram_di_scope import _TelegramUpdate, TelegramUpdateScopeDecorator
from voice_bot.voice_bot_configurator import VoiceBotConfigurator


@singleton
class VoiceBotRunner:
    @inject
    def __init__(
            self,
            configuration: VoiceBotConfigurator,
            injector: Injector,
            middleware: TelegramUpdateScopeDecorator,
            tg_bot_proxy: TelegramBotProxy
    ):
        self._logger = structlog.get_logger(class_name=__class__.__name__)

        self._middleware = middleware

        self._injector = injector

        self._application = Application.builder().token(configuration.telegram_bot_token).build()

        self._wire_commands()
        self._wire_callback_handler()
        self._wire_text_message_handler()
        self._wire_cron_jobs()

        tg_bot_proxy.push_bot(self._application.bot)

    def start_bot(self) -> None:
        self._application.run_polling()

    def _wire_commands(self) -> None:
        for name, cmd in COMMANDS.items():
            wrapper = _HandlerWrapper(name, cmd, self._injector, self._logger)
            self._application.add_handler(CommandHandler(name, self._middleware(wrapper.handle)))

    def _wire_callback_handler(self) -> None:
        wrapper = _CallbackQueryHandlerWrapper(self._injector, self._logger)
        self._application.add_handler(CallbackQueryHandler(self._middleware(wrapper.handle)))

    def _wire_cron_jobs(self) -> None:
        for name, job in CRON_JOBS.items():
            handler = _CronHandlerWrapper(self._injector, job, self._logger)

            if job.interval == timedelta.max:
                self._application.job_queue.run_once(
                    callback=self._middleware(handler.handle),
                    when=datetime.utcnow()
                )
                continue

            self._application.job_queue.run_repeating(
                callback=self._middleware(handler.handle),
                interval=job.interval,
                first=job.first,
                last=job.last,
                name=name
            )

    def _wire_text_message_handler(self) -> None:
        async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
            with bound_contextvars(local_request_id=str(uuid.uuid4())):
                try:
                    await self._logger.info("Got text message", telegram_update=update.to_json())
                    handler = self._injector.get(TextMessageHandler, _TelegramUpdate)
                    await handler.handle(update, context)
                except Exception as e:
                    await self._logger.exception(e)
                    raise

        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._middleware(handle)))


class _HandlerWrapper:
    def __init__(self, cmd_name: str, cmd_def: CommandDefinition, injector: Injector, logger):
        self._logger = logger
        self._injector = injector
        self._cmd_name = cmd_name
        self._cmd_def = cmd_def
        self._stopwatch = Stopwatch()

        self._alarm = self._injector.get(ErrorsMessenger)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with bound_contextvars(local_request_id=str(uuid.uuid4())):
            self._stopwatch.start()
            try:
                await self._logger.debug("Got update", telegram_update=update.to_json())

                for claim in self._cmd_def.claims:
                    if not await self._injector.get(claim.base_class, _TelegramUpdate).check(
                        str(update.effective_user.id), claim
                    ):
                        return

                handler = self._injector.get(self._cmd_def.handler, _TelegramUpdate)
                if isinstance(self._cmd_def, CommandWithMenuDefinition) \
                        and isinstance(handler, NavigationCommandHandler):
                    handler.push_nav_tree(self._cmd_def.navigation)

                await handler.handle(update, context)

            except Exception as e:
                await self._logger.exception(e)
                await self._alarm.alarm(e)

            finally:
                await self._logger.info("Update processed", req_time=self._stopwatch.stop())


class _CallbackQueryHandlerWrapper:
    def __init__(self, injector: Injector, logger):
        self._logger = logger
        self._injector = injector
        self._stopwatch = Stopwatch()

        self._alarm = self._injector.get(ErrorsMessenger)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        with bound_contextvars(local_request_id=str(uuid.uuid4())):
            self._stopwatch.start()
            try:
                await self._logger.debug("Got callback update", telegram_update=update.to_json())
                handler = self._injector.get(NavigationCommandHandler, _TelegramUpdate)
                await handler.handle_callback(update, context)

            except Exception as e:
                await self._logger.exception(e)
                await self._alarm.alarm(e)

            finally:
                await self._logger.info("Callback processed", req_time=self._stopwatch.stop())


class _CronHandlerWrapper:
    def __init__(self, injector: Injector, cron_def: CronJob, logger):
        self._cron_def = cron_def
        self._logger = logger
        self._injector = injector
        self._stopwatch = Stopwatch()

        self._alarm = self._injector.get(ErrorsMessenger)

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        self._stopwatch.start()

        with bound_contextvars(local_request_id=str(uuid.uuid4())):
            try:
                await self._logger.debug("Cron started", cron=json.dumps(self._cron_def, default=str))
                handler = self._injector.get(self._cron_def.handler, _TelegramUpdate)
                await handler.handle(context)

            except Exception as e:
                await self._logger.exception(e)
                await self._alarm.alarm(e)

            finally:
                await self._logger.info("Cron processed", req_time=self._stopwatch.stop())

