from datetime import datetime, timedelta

import sqlalchemy.sql.functions
from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from voice_bot.constants import LESSONS_THRESHOLD
from voice_bot.db.enums import DumpStates, ScheduleRecordType
from voice_bot.db.models import StandardScheduleRecord, User, ScheduleRecord
from voice_bot.db.shortcuts import is_active
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, str_hours_from_dt, dt_fmt_rus, dt_fmt_time, \
    to_monday_midnight, td_days_and_str_hours, to_midnight
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

    # no commit
    async def create_lessons_from_std_schedule(self, on_date: datetime) -> list[ScheduleRecord]:
        std = await self.get_standard_schedule(None)
        from_monday = to_monday_midnight(on_date)
        to_monday = to_monday_midnight(LESSONS_THRESHOLD + on_date)

        created_lessons: list[ScheduleRecord] = []

        current_monday = from_monday
        while current_monday <= to_monday:
            next_monday = current_monday + timedelta(days=7)

            query = select(ScheduleRecord).options(joinedload(ScheduleRecord.user)).where(
                ScheduleRecord.absolute_start_time.between(current_monday, next_monday))
            lessons = (await self._session.scalars(query)).all()
            lessons_dict = \
                {td_days_and_str_hours(lesson.absolute_start_time.weekday(), lesson.time_start): lesson for lesson in
                 lessons}

            for std_lesson in std:
                key = td_days_and_str_hours(std_lesson.day_of_the_week, std_lesson.time_start)
                if key not in lessons_dict:
                    start_time = current_monday + key

                    if start_time < on_date:
                        continue

                    new_lesson = ScheduleRecord(
                        user=std_lesson.user,
                        absolute_start_time=start_time,
                        time_start=std_lesson.time_start,
                        time_end=std_lesson.time_end,
                        type=ScheduleRecordType.OFFLINE,
                        dump_state=DumpStates.ACTIVE
                    )
                    created_lessons.append(new_lesson)
                    self._session.add(new_lesson)
                    lessons_dict[key] = new_lesson

            current_monday = next_monday

        return created_lessons

    # no commit
    async def clean_up_elder_lessons(self, on_date: datetime) -> int:
        monday = to_monday_midnight(on_date)
        lessons = await self.get_schedule(datetime.min, monday)

        for lesson in lessons:
            await self._session.delete(lesson)

        return len(lessons)

    async def cancel_lessons_on_day(self, on_day: datetime) -> bool:
        lessons = await self.get_schedule_for_day(on_day)

        if not lessons:
            return False

        for lesson in lessons:
            lesson.dump_state = DumpStates.BOT_DELETED

        await self._session.commit()

        date_rus = dt_fmt_rus(lessons[0].absolute_start_time)
        to_admin = [f"Отменены уроки в {date_rus} и отправлены уведомления:"]
        message = f"Привет! Занятия в {date_rus} были отменены!"
        for lesson in lessons:
            to_admin.append(f"- в {lesson.time_start} с {lesson.user.fullname}")
            await self.users.send_text_message(lesson.user, message)

        await self.users.send_text_message_to_admins("\n".join(to_admin))
        return True

    async def get_schedule_for_day(self, day: datetime) -> list[ScheduleRecord]:
        midnight = to_midnight(day)
        return await self.get_schedule(midnight, midnight + timedelta(hours=23, minutes=59))

    async def count_active_lessons_on_day(self, day: datetime) -> int:
        midnight = to_midnight(day)
        return await self.count_active_lessons(midnight, midnight + timedelta(hours=23, minutes=59))

    async def count_active_lessons(self, date_start: datetime, date_end: datetime) -> int:
        query = select([sqlalchemy.sql.functions.count]) \
            .select_from(ScheduleRecord) \
            .where(
                ScheduleRecord.absolute_start_time.between(date_start, date_end) & is_active(ScheduleRecord))
        return await self._session.scalar(query)

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

    async def swap_lessons(self, lesson1: ScheduleRecord, lesson2: ScheduleRecord):
        lesson1.user, lesson2.user = lesson2.user, lesson1.user
        lesson1.dump_state = DumpStates.TO_SYNC
        lesson2.dump_state = DumpStates.TO_SYNC
        await self._session.commit()
        await self.users.send_text_message_to_admins(
            f"Уроки учеников {lesson1.user.fullname} и {lesson2.user.fullname} поменяны местами, теперь: "
            f"\n🥕 урок {dt_fmt_time(lesson1.absolute_start_time)} у {lesson1.user.fullname}"
            f"\n🥕 урок {dt_fmt_time(lesson2.absolute_start_time)} у {lesson2.user.fullname}")

