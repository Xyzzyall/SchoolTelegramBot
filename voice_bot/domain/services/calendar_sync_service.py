from datetime import timedelta

import structlog
from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from voice_bot.calendar.google_calendar import GoogleCalendarService
from voice_bot.db.models import ScheduleRecord
from voice_bot.db.update_session import UpdateSession
from voice_bot.misc.datetime_service import DatetimeService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CalendarSyncService:
    @inject
    def __init__(self, gc: GoogleCalendarService, session: UpdateSession, dt: DatetimeService):
        self._dt = dt
        self._session = session.session
        self._gc = gc

        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def sync(self):
        try:
            await self._logger.info("starting google calendar sync")
            await self._gc.init_events()
            lessons = (await self._session.scalars(select(ScheduleRecord).options(joinedload(ScheduleRecord.user)))).all()
            for lesson in lessons:
                await self._gc.sync_event(lesson)
            await self._gc.clean_old_events(self._dt.now() - timedelta(days=14))
            await self._logger.info("google calendar events synced")
        finally:
            await self._session.commit()
