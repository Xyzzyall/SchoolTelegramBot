from datetime import datetime
from typing import Optional

import structlog
from injector import inject
from sqlalchemy import select

from voice_bot.db.enums import ScheduleRecordType, DumpStates, YesNo
from voice_bot.db.models import User, ScheduleRecord, FreeLesson
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import to_midnight, to_day_end, str_hours_from_dt, dt_fmt_rus, dt_fmt_time
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class BookLessonsService:
    _free_lessons: dict[datetime, FreeLesson] = {}

    @inject
    def __init__(self, schedule: ScheduleService, session: UpdateSession, users: UsersService):
        self.users = users
        self._session = session()
        self._schedule = schedule
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def book_lesson(self, user: User, dt: datetime) -> ScheduleRecord | None:
        free_lessons = await self.get_free_lessons(dt)
        time_start = str_hours_from_dt(dt)
        if time_start not in free_lessons:
            return None

        free = free_lessons[time_start]

        query = select(ScheduleRecord).where(ScheduleRecord.absolute_start_time == dt)
        lesson = await self._session.scalar(query)

        if lesson:
            lesson.user_id = user.id
            lesson.dump_state = DumpStates.TO_SYNC
        else:
            lesson = ScheduleRecord(
                user=user,
                absolute_start_time=dt,
                time_start=free.time_start,
                time_end=free.time_end,
                type=ScheduleRecordType.OFFLINE,
                dump_state=DumpStates.TO_SYNC
            )
            self._session.add(lesson)

        await self._session.commit()
        await self.users.send_text_message_to_admins(f"Ученик {user.fullname} успешно записан на {dt_fmt_time(dt)}")
        return lesson

    async def move_lesson(self, lesson: ScheduleRecord, dt: datetime) -> ScheduleRecord:
        # will stay before I delete google spreadsheets integration
        new_lesson = await self.book_lesson(lesson.user, dt)
        lesson.dump_state = DumpStates.BOT_DELETED
        await self._session.commit()
        await self.users.send_text_message_to_admins(
            f"Урок ученика {lesson.user.fullname} успешно перемещен с "
            f"{dt_fmt_time(lesson.absolute_start_time)} на {dt_fmt_time(dt)}")
        return new_lesson

    async def get_free_lessons(self, on_day: datetime, show_vacant: bool = True) \
            -> dict[str, (FreeLesson, ScheduleRecord)]:
        queue = select(FreeLesson)\
            .where((FreeLesson.weekday == on_day.weekday()) & (FreeLesson.is_active == YesNo.YES))

        res = {free.time_start: free for free in (await self._session.scalars(queue)).all()}
        if show_vacant:
            lessons = await self._schedule.get_schedule(to_midnight(on_day), to_day_end(on_day))
            for lesson in lessons:
                if lesson.time_start in res:
                    del res[lesson.time_start]

        return res

    async def get_all_free_lessons(self) -> list[FreeLesson]:
        queue = select(FreeLesson).where((FreeLesson.is_active == YesNo.YES))
        return await self._session.scalars(queue)

    async def get_free_lessons_weekday(self, weekday: int) -> dict[str, FreeLesson]:
        queue = select(FreeLesson).where((FreeLesson.is_active == YesNo.YES) & (FreeLesson.weekday == weekday))
        return {lesson.time_start: lesson for lesson in await self._session.scalars(queue)}

    async def get_free_lesson_by_id(self, id: int, only_active: bool = False) -> FreeLesson | None:
        queue = select(FreeLesson).where((FreeLesson.id == id) & (FreeLesson.is_active == YesNo.YES)) if only_active\
            else select(FreeLesson).where((FreeLesson.id == id))
        return await self._session.scalar(queue)

    async def get_free_lesson(self, weekday: int, time_start: str, time_end: str) -> FreeLesson | None:
        queue = select(FreeLesson).where((FreeLesson.weekday == weekday) &
                                         (FreeLesson.time_start == time_start) &
                                         (FreeLesson.time_end == time_end))
        return await self._session.scalar(queue)

    async def toggle_free_lesson(self, weekday: int, time_start: str, time_end: str):
        lesson = await self.get_free_lesson(weekday, time_start, time_end)
        if not lesson:
            await self.create_free_lesson(weekday, time_start, time_end)
            return
        lesson.is_active = YesNo.YES if lesson.is_active == YesNo.NO else YesNo.NO
        await self._session.commit()

    async def try_get_free_lesson(self, dt: datetime):
        lessons = await self.get_free_lessons(dt)
        return lessons.get(str_hours_from_dt(dt))

    async def create_free_lesson(self, weekday: int, time_start: str, time_end: str):
        maybe_lesson = await self.get_free_lesson(weekday, time_start, time_end)
        if maybe_lesson and maybe_lesson.is_active == YesNo.NO:
            maybe_lesson.is_active = YesNo.YES
            await self._session.commit()
            return

        lesson = FreeLesson(weekday=weekday, time_start=time_start, time_end=time_end, is_active=YesNo.YES)
        self._session.add(lesson)
        await self._session.commit()



