from datetime import datetime

from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from voice_bot.db.models import StandardScheduleRecord, User, ScheduleRecord
from voice_bot.db.shortcuts import is_active
from voice_bot.db.update_session import UpdateSession
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class ScheduleService:
    @inject
    def __init__(self,
                 session: UpdateSession,
                 params: ParamsTableService):
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
            (ScheduleRecord.absolute_start_time > datetime.now()) & is_active(ScheduleRecord)
        ).order_by(ScheduleRecord.absolute_start_time).limit(1)
        return await self._session.scalar(query)

    async def get_next_lesson_for(self, user: User) -> ScheduleRecord | None:
        query = select(ScheduleRecord).where(
            (ScheduleRecord.user_id == user.id) & (ScheduleRecord.absolute_start_time > datetime.now())
            & is_active(ScheduleRecord)
        ).order_by(ScheduleRecord.absolute_start_time).limit(1)
        return await self._session.scalar(query)
