from dataclasses import dataclass, field
from datetime import datetime, timedelta

import structlog
from injector import inject
from sortedcontainers import SortedList
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from voice_bot.db.enums import UserActionType
from voice_bot.db.models import User, UserActions, ScheduleRecord
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, to_midnight
from voice_bot.telegram_di_scope import telegramupdate


@dataclass
class SubscriptionTemplate:
    lessons: int
    cancellations: int
    timespan: timedelta

    def __str__(self):
        return f"{self.lessons} уроков, {self.cancellations} отмен на {int(self.timespan.days / 7)} недель"


SUBSCRIPTIONS = [
    SubscriptionTemplate(1, 0, timedelta(days=3)),
    SubscriptionTemplate(4, 2, timedelta(days=7*5)),
    SubscriptionTemplate(8, 2, timedelta(days=7*6)),
    SubscriptionTemplate(20, 4, timedelta(days=7*10)),
]


@dataclass
class Subscription:
    lessons: int
    cancellations: int
    valid_from: datetime
    valid_to: datetime

    counted_lessons: int = field(default=0)
    counted_cancellations: int = field(default=0)

    is_stub: bool = field(default=False)

    def try_add_lesson(self, dt: datetime) -> bool:
        if not self.is_stub and (self.lessons == self.counted_lessons or not self.valid_from < dt < self.valid_to):
            return False
        self.counted_lessons += 1
        return True

    def try_add_cancel(self, dt: datetime) -> bool:
        if not self.is_stub and \
                (self.cancellations == self.counted_cancellations or not self.valid_from < dt < self.valid_to):
            return False
        self.counted_cancellations += 1
        return True

    def is_valid(self, dt: datetime):
        return self.valid_from <= dt <= self.valid_to

    def is_exhausted(self):
        return self.is_stub or self.lessons >= self.counted_lessons

    @staticmethod
    def stub() -> "Subscription":
        return Subscription(lessons=0, cancellations=0, valid_from=datetime.min, valid_to=datetime.max, is_stub=True)


@telegramupdate
class ActionsLoggerService:
    @inject
    def __init__(self, session: UpdateSession, dt: DatetimeService, users: UsersService):
        self._users = users
        self._dt = dt
        self._session = session.session
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def log_lesson(self, user: User):
        self._session.add(UserActions(
            user=user,
            user_unique_name=user.unique_name,
            action_type=UserActionType.LESSON,
            log_date=self._dt.now()
        ))
        await self._session.commit()

    async def log_cancellation(self, user: User):
        self._session.add(UserActions(
            user=user,
            user_unique_name=user.unique_name,
            action_type=UserActionType.LESSON_CANCELLATION,
            log_date=self._dt.now()
        ))
        await self._session.commit()

    async def autolog_lesson(self, for_time: datetime):
        from_time = for_time - timedelta(hours=1, minutes=15)
        to_time = for_time - timedelta(minutes=15)
        query = select(ScheduleRecord)\
            .where(ScheduleRecord.absolute_start_time.between(from_time, to_time))\
            .options(joinedload(ScheduleRecord.user))

        users_to_check: list[User] = []
        completed_lessons = (await self._session.scalars(query)).all()
        for lesson in completed_lessons:
            self._session.add(UserActions(
                user=lesson.user,
                user_unique_name=lesson.user.unique_name,
                action_type=UserActionType.LESSON,
                log_date=self._dt.now()
            ))
            users_to_check.append(lesson.user)

        await self._session.commit()
        await self._logger.info(
            "logged completed lessons",
            lessons=[{"user": lesson.user.unique_name, "lesson_start": lesson.absolute_start_time}
                     for lesson in completed_lessons]
        )

        for user in users_to_check:
            subs = await self.count_subscriptions_on_date(user, for_time)
            remain_lessons = 0
            for s in subs:
                if s.is_valid(for_time) and s.lessons == 1:
                    remain_lessons = -1
                    break

                if s.is_valid(for_time):
                    diff = s.lessons - s.counted_lessons
                    remain_lessons += diff if diff > 0 else 0

            if remain_lessons == 0:
                await self._users.send_text_message_to_admins(f"У ученика {user.fullname} кончился абонемент!")

    async def log_subscription(
            self,
            user: User,
            template: SubscriptionTemplate,
            from_date: datetime):
        sub = UserActions(
            user=user,
            user_unique_name=user.unique_name,
            action_type=UserActionType.SUBSCRIPTION,
            log_date=self._dt.now()
        )
        sub.subs_quantity = template.lessons
        sub.subs_cancellations = template.cancellations
        sub.subs_valid_from = to_midnight(from_date)
        sub.subs_valid_to = sub.subs_valid_from + template.timespan
        self._session.add(sub)
        await self._session.commit()

    def migrate_subscription_and_lessons(self, user: User, exhausted: int, lessons: int) -> bool:
        def subscription_for_lessons() -> SubscriptionTemplate | None:
            for sub in SUBSCRIPTIONS:
                if sub.lessons == lessons:
                    return sub
            return None

        sub_t = subscription_for_lessons()
        if not sub_t:
            return False

        sub = UserActions(
            user=user,
            user_unique_name=user.unique_name,
            action_type=UserActionType.SUBSCRIPTION,
            log_date=self._dt.now()
        )
        sub.subs_quantity = sub_t.lessons
        sub.subs_cancellations = sub_t.cancellations
        sub.subs_valid_from = to_midnight(self._dt.now())
        sub.subs_valid_to = sub.subs_valid_from + sub_t.timespan
        self._session.add(sub)

        for _ in range(exhausted):
            self._session.add(UserActions(
                user=user,
                user_unique_name=user.unique_name,
                action_type=UserActionType.LESSON,
                log_date=self._dt.now()
            ))
        return True

    async def count_subscriptions_on_date(self, user: User, dt: datetime) -> list[Subscription]:
        query = select(UserActions).where(
            (UserActions.user == user)
            & UserActions.log_date.between(dt - timedelta(days=90), to_midnight(dt) + timedelta(days=1))
            ).order_by(UserActions.log_date)
        actions = (await self._session.scalars(query)).all()

        res = SortedList[Subscription](key=lambda x: x.valid_from)
        res.add(Subscription.stub())
        for action in actions:
            if action.action_type == UserActionType.SUBSCRIPTION:
                res.add(Subscription(
                    lessons=action.subs_quantity,
                    cancellations=action.subs_cancellations,
                    valid_from=action.subs_valid_from,
                    valid_to=action.subs_valid_to
                ))

        for action in actions:
            match action.action_type:
                case UserActionType.LESSON | UserActionType.LESSON_CANCELLATION:
                    for sub in reversed(res):
                        sub: Subscription
                        if not sub.is_valid(action.log_date):
                            continue
                        if action.action_type == UserActionType.LESSON:
                            if sub.try_add_lesson(action.log_date):
                                break
                        else:
                            if sub.try_add_cancel(action.log_date):
                                break

        return [v for v in res]
