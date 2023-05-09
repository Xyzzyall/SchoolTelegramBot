import structlog
from injector import inject
from telegram.ext import ContextTypes

from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.actions_logger import ActionsLoggerService
from voice_bot.misc.datetime_service import DatetimeService
from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CronLessonLogger(BaseScheduleHandler):
    @inject
    def __init__(self,
                 session: UpdateSession,
                 log: ActionsLoggerService,
                 dt: DatetimeService):
        self._dt = dt
        self._log = log
        self._session = session.session
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self._log.autolog_lesson(self._dt.now())
        except Exception as e:
            await self._session.rollback()
            await self._logger.error("error while logging completed lessons", exception=e)