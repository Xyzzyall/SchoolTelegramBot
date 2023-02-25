from dataclasses import dataclass
from datetime import timedelta, datetime

from injector import inject
from sqlalchemy import select, text

from voice_bot.constants import REMINDERS_OPTIONS, REMINDER_THRESHOLD
from voice_bot.db.enums import YesNo
from voice_bot.db.models import User, UserLessonReminder, ScheduleRecord
from voice_bot.db.shortcuts import is_active
from voice_bot.db.update_session import UpdateSession
from voice_bot.telegram_di_scope import telegramupdate


@dataclass
class FiredReminder:
    chat_id: str
    minutes: int
    lesson: ScheduleRecord


@telegramupdate
class RemindersService:
    @inject
    def __init__(self, session: UpdateSession):
        self._session = session()

    @staticmethod
    def _get_reminder_by_key(reminder_key: str) -> timedelta:
        return REMINDERS_OPTIONS[reminder_key]

    async def _user_reminder(self, user: User, minutes: int) -> UserLessonReminder:
        query = select(UserLessonReminder).where(
            (UserLessonReminder.user_id == user.id)
            & (UserLessonReminder.remind_minutes_before == minutes)).limit(1)
        reminder = await self._session.scalar(query)

        if not reminder:
            new_reminder = UserLessonReminder(user=user, remind_minutes_before=minutes, is_active=YesNo.NO)
            self._session.add(new_reminder)
            return new_reminder

        return reminder

    async def switch_reminder_for(self, user: User, reminder_type: str):
        delta = self._get_reminder_by_key(reminder_type)
        reminder = await self._user_reminder(user, int(delta.total_seconds() / 60))

        reminder.is_active = YesNo.YES if reminder.is_active == YesNo.NO else YesNo.NO

        await self._session.commit()

    async def get_reminder_state_for(self, user: User, reminder_type: str) -> bool:
        delta = self._get_reminder_by_key(reminder_type)
        reminder = await self._user_reminder(user, int(delta.total_seconds() / 60))
        return reminder.is_active == YesNo.YES

    async def get_active_reminders_for(self, user: User) -> list[timedelta]:
        query = select(UserLessonReminder.remind_minutes_before).where(
            (UserLessonReminder.user_id == user.id) & (UserLessonReminder.is_active == YesNo.YES)
        )
        return [timedelta(minutes=minutes) for minutes in (await self._session.scalars(query)).all()]

    _USER_FIRED_REMINDERS_SQL = text("""
        SELECT DISTINCT u.telegram_chat_id "chat_id", u_r.remind_minutes_before "minutes", s.* FROM "USERS" u
        JOIN "USERS_REMINDERS" u_r on u.id = u_r.user_id
        JOIN "SCHEDULE" s on u.id = s.user_id
        WHERE 1=1
            AND u.dump_state IN ('ACTIVE', 'TO_SYNC')
            AND s.dump_state IN ('ACTIVE', 'TO_SYNC')
            AND s.type != 'RENT'
            AND s.absolute_start_time - u_r.remind_minutes_before * '1 minute'::interval BETWEEN :start and :end
    """)

    async def get_fired_reminders_at(self, time: datetime) -> list[FiredReminder]:
        start, end = time - REMINDER_THRESHOLD, time + REMINDER_THRESHOLD
        res = await self._session.execute(self._USER_FIRED_REMINDERS_SQL, {
            "start": start,
            "end": end
        })
        return [FiredReminder(row.chat_id, row.minutes, row) for row in res.all()]

    async def get_fired_reminders_for_admin_at(self, admin: User, time: datetime) -> list[ScheduleRecord]:
        admin_reminders = (await self._session.scalars(
            select(UserLessonReminder.remind_minutes_before).where(
                (UserLessonReminder.user_id == admin.id) & (UserLessonReminder.is_active == YesNo.YES)
            )
        )).all()
        if not admin_reminders:
            return []

        start = time - REMINDER_THRESHOLD + timedelta(minutes=min(admin_reminders))
        end = time + REMINDER_THRESHOLD + timedelta(minutes=max(admin_reminders))

        query = select(ScheduleRecord).where(
            is_active(ScheduleRecord) & ScheduleRecord.absolute_start_time.between(start, end)
        )
        return (await self._session.scalars(query)).all()

