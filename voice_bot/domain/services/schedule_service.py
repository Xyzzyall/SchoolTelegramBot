from datetime import datetime, timedelta

from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from voice_bot.db.enums import DumpStates
from voice_bot.db.models import StandardScheduleRecord, User, ScheduleRecord
from voice_bot.db.shortcuts import is_active
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, str_hours_from_dt, dt_fmt_rus, dt_fmt_time
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class ScheduleService:
    @inject
    def __init__(self,
                 session: UpdateSession,
                 params: ParamsTableService,
                 dt: DatetimeService,
                 users: UsersService):
        self.users = users
        self._dt = dt
        self._session = session()
        self._params = params

    async def get_standard_schedule(self, days_of_the_week: list[int] | None = None) -> list[StandardScheduleRecord]:
        query = select(StandardScheduleRecord).options(joinedload(StandardScheduleRecord.user))
        if days_of_the_week:
            query = query.where(StandardScheduleRecord.day_of_the_week.in_(days_of_the_week))
        return (await self._session.scalars(query.order_by(StandardScheduleRecord.day_of_the_week))).all()

    async def get_standard_schedule_for(
            self,
            user: User,
            days_of_the_week: list[int] | None = None
    ) -> list[StandardScheduleRecord]:
        query = select(StandardScheduleRecord).where(
            (StandardScheduleRecord.user_id == user.id) & is_active(StandardScheduleRecord))
        if days_of_the_week:
            query = query.where(StandardScheduleRecord.day_of_the_week.in_(days_of_the_week))

        return (await self._session.scalars(query.order_by(StandardScheduleRecord.day_of_the_week))).all()

    async def get_schedule(self, date_start: datetime, date_end: datetime) -> list[ScheduleRecord]:
        query = select(ScheduleRecord).options(joinedload(ScheduleRecord.user)).where(
            ScheduleRecord.absolute_start_time.between(date_start, date_end) & is_active(ScheduleRecord)
        ).order_by(ScheduleRecord.absolute_start_time)
        return (await self._session.scalars(query)).all()

    async def get_schedule_for(self, date_start: datetime, date_end: datetime, user: User) -> list[ScheduleRecord]:
        query = select(ScheduleRecord).where(
            (ScheduleRecord.user_id == user.id) & ScheduleRecord.absolute_start_time.between(date_start, date_end)
            & is_active(ScheduleRecord)
        ).order_by(ScheduleRecord.absolute_start_time)
        return (await self._session.scalars(query)).all()

    async def get_next_lesson(self) -> ScheduleRecord | None:
        query = select(ScheduleRecord).options(joinedload(ScheduleRecord.user)).where(
            (ScheduleRecord.absolute_start_time > self._dt.now()) & is_active(ScheduleRecord)
        ).order_by(ScheduleRecord.absolute_start_time).limit(1)
        return await self._session.scalar(query)

    async def get_next_lesson_for(self, user: User) -> ScheduleRecord | None:
        query = select(ScheduleRecord).where(
            (ScheduleRecord.user_id == user.id) & (ScheduleRecord.absolute_start_time > self._dt.now())
            & is_active(ScheduleRecord)
        ).order_by(ScheduleRecord.absolute_start_time).limit(1)
        return await self._session.scalar(query)

    async def get_lesson_by_id(self, lesson_id: int) -> ScheduleRecord | None:
        query = select(ScheduleRecord).where((ScheduleRecord.id == lesson_id) & is_active(ScheduleRecord)) \
            .options(joinedload(ScheduleRecord.user))
        return await self._session.scalar(query)

    async def cancel_lesson(self, lesson_id: int, user_id: int = -1) -> bool:
        query = select(ScheduleRecord).where((ScheduleRecord.id == lesson_id) & is_active(ScheduleRecord)) \
            .options(joinedload(ScheduleRecord.user))
        lesson: ScheduleRecord | None = await self._session.scalar(query)
        if not lesson or 0 < user_id != lesson.user.id:
            return False
        lesson.dump_state = DumpStates.BOT_DELETED
        await self._session.commit()
        await self.users.send_text_message_to_admins(
            f"Урок ученика {lesson.user.fullname} в {dt_fmt_time(lesson.absolute_start_time)} был отменен.")
        return True

    async def move_lesson_to(self, lesson: ScheduleRecord, to_date: datetime):
        lesson.absolute_start_time = to_date
        lesson.time_start = str_hours_from_dt(to_date)
        lesson.time_end = str_hours_from_dt(to_date + timedelta(minutes=50))
        lesson.dump_state = DumpStates.TO_SYNC
        await self._session.commit()

    async def swap_lessons(self, lesson1: ScheduleRecord, lesson2: ScheduleRecord):
        lesson1.user, lesson2.user = lesson2.user, lesson1.user
        lesson1.dump_state = DumpStates.TO_SYNC
        lesson2.dump_state = DumpStates.TO_SYNC
        await self._session.commit()
        await self.users.send_text_message_to_admins(
            f"Уроки учеников {lesson1.user.fullname} и {lesson2.user.fullname} поменяны местами, теперь: "
            f"\n🥕 урок {dt_fmt_time(lesson1.absolute_start_time)} у {lesson1.user.fullname}"
            f"\n🥕 урок {dt_fmt_time(lesson2.absolute_start_time)} у {lesson2.user.fullname}")

