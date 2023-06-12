from datetime import datetime, timedelta

import structlog
from gcsa.attendee import Attendee
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
from injector import singleton, inject

from voice_bot.db.enums import ScheduleRecordType
from voice_bot.db.models import ScheduleRecord
from voice_bot.misc.datetime_service import DatetimeService, cut_timezone
from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.voice_bot_configurator import VoiceBotConfigurator


@singleton
class GoogleCalendarService:
    @inject
    def __init__(self, conf: VoiceBotConfigurator, dt: DatetimeService, gs: GspreadClient):
        self._gs = gs
        self._dt = dt
        self._conf = conf
        self._gc = GoogleCalendar(credentials_path=conf.oauth_credentials)
        self._logger = structlog.get_logger(class_name=__class__.__name__)

        self._events: dict[str, Event] | None = None

    async def init_events(self):
        if self._events:
            return

        self._events = {}
        for event in self._gc:
            if event.summary.startswith("Voice city."):
                self._events[event.id] = event
        await self._logger.info("events fetched", count=len(self._events))

    async def create(self, lesson: ScheduleRecord):
        if self._events is None:
            raise RuntimeError("events are not initialized")

        if lesson.gc_event_id:
            raise RuntimeError(f"cannot create more than 1 for one lesson, lesson_id={lesson.id}")

        e = Event(
            summary=self._summary_for(lesson),
            start=lesson.absolute_start_time,
            end=lesson.absolute_start_time + timedelta(minutes=50),
            timezone=self._dt.timezone.zone,
            attendees=[Attendee(email=self._conf.calendar_email)],
            description=await self._desc_for(lesson)
        )
        try:
            e = self._gc.add_event(e)
            lesson.gc_event_id = e.event_id
            self._events[e.event_id] = e
            await self._logger.info("event created", lesson_id=lesson.id)
        except:
            if e.event_id in self._events:
                del self._events[lesson.gc_event_id]
            lesson.gc_event_id = None

    def get(self, event_id: str) -> Event:
        if self._events is None:
            raise RuntimeError("events are not initialized")
        return self._gc.get_event(event_id)

    async def sync_event(self, lesson: ScheduleRecord):
        if self._events is None:
            raise RuntimeError("events are not initialized")

        if not lesson.gc_event_id:
            await self.create(lesson)
            return

        e = self.get(lesson.gc_event_id)
        new_desc = await self._desc_for(lesson)
        new_summary = self._summary_for(lesson)
        if new_summary != e.summary or new_desc != e.description:
            e.description = new_desc
            e.summary = new_summary
            self._gc.update_event(e)
            await self._logger.info("calendar event updated")

    async def clean_old_events(self, delete_before: datetime):
        if self._events is None:
            raise RuntimeError("events are not initialized")

        for k, e in [*self._events.items()]:
            e: Event
            if cut_timezone(e.start) < delete_before:
                self._gc.delete_event(e)
                del self._events[k]
                await self._logger.info("event deleted", start=e.start)

    @staticmethod
    def _summary_for(lesson: ScheduleRecord) -> str:
        return f"Voice city. Занятие с {lesson.user.fullname}"

    async def _desc_for(self, lesson: ScheduleRecord) -> str:
        return f"{'Онлайн' if lesson.type == ScheduleRecordType.ONLINE else 'Очное'} занятие\n" + \
               f"Место проведения: {lesson.location if lesson.location else 'не указано'}\n\n" + \
               await self._gs.get_link_to_schedule_worksheet(lesson.absolute_start_time)
