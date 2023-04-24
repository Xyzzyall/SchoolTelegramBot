from dataclasses import dataclass
from datetime import datetime, timedelta

from injector import singleton, inject

from voice_bot.db.enums import ScheduleRecordType, DumpStates
from voice_bot.db.models import User, ScheduleRecord
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.telegram_di_scope import telegramupdate


@dataclass
class FreeLesson:
    lesson_datetime: datetime
    time_start: str
    time_end: str


@telegramupdate
class BookLessonsService:
    _free_lessons: dict[datetime, FreeLesson] = {}

    @inject
    def __init__(self, schedule: ScheduleService, session: UpdateSession):
        self._session = session()
        self._schedule = schedule

    async def book_lesson(self, user: User, dt: datetime) -> ScheduleRecord | None:
        if dt not in BookLessonsService._free_lessons:
            return None

        lessons = await self._schedule.get_schedule(dt - timedelta(minutes=10), dt + timedelta(minutes=10))
        if lessons:
            del BookLessonsService._free_lessons[dt]
            return None

        free = BookLessonsService._free_lessons[dt]
        new_record = ScheduleRecord(
            user=user,
            absolute_start_time=free.lesson_datetime,
            time_start=free.time_start,
            time_end=free.time_end,
            type=ScheduleRecordType.OFFLINE,
            dump_state=DumpStates.TO_SYNC
        )
        self._session.add(new_record)
        await self._session.commit()
        del BookLessonsService._free_lessons[dt]
        return new_record

    @staticmethod
    def set_free_lessons(lessons: list[FreeLesson]):
        BookLessonsService._free_lessons.clear()
        for lesson in lessons:
            BookLessonsService._free_lessons[lesson.lesson_datetime] = lesson

    @staticmethod
    def get_free_lessons_for(start: datetime, end: datetime) -> list[FreeLesson]:
        res = []
        for lesson in BookLessonsService._free_lessons.values():
            if start <= lesson.lesson_datetime <= end:
                res.append(lesson)
        return res

    @staticmethod
    def try_get_free_lesson(dt: datetime):
        if dt not in BookLessonsService._free_lessons:
            return None
        return BookLessonsService._free_lessons[dt]
