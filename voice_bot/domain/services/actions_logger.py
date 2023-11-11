from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import reduce

import structlog
from injector import inject
from sortedcontainers import SortedList
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from voice_bot.db.enums import UserActionType
from voice_bot.db.models import User, UserActions, ScheduleRecord
from voice_bot.db.shortcuts import is_active
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, to_midnight, to_day_end
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

    lesson_dates: list[datetime] = field(default_factory=list)
    counted_lessons: int = field(default=0)
    cancellation_dates: list[datetime] = field(default_factory=list)
    counted_cancellations: int = field(default=0)

    is_stub: bool = field(default=False)

    def try_add_lesson(self, dt: datetime) -> bool:
        if not self.is_stub and (self.lessons <= self.counted_lessons or not self.is_valid(dt)):
            return False
        self.lesson_dates.append(dt)
        self.counted_lessons += 1
        return True

    def try_add_cancel(self, dt: datetime) -> bool:
        if not self.is_stub and \
                (self.cancellations == self.counted_cancellations or not self.is_valid(dt)):
            return False
        self.cancellation_dates.append(dt)
        self.counted_cancellations += 1
        return True

    def is_valid(self, dt: datetime):
        return self.valid_from <= dt <= to_day_end(self.valid_to)

    def is_exhausted(self):
        return self.is_stub or self.counted_lessons >= self.lessons

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

    async def log_lesson(self, user: User, dt: datetime = None):
        self._session.add(UserActions(
            user=user,
            user_unique_name=user.unique_name,
            action_type=UserActionType.LESSON,
            log_date=self._dt.now() if not dt else dt
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

    async def get_actions_for_user(self, user: User, dt_from: datetime, dt_to: datetime) -> list[UserActions]:
        query = select(UserActions) \
            .where((UserActions.user == user) &
                   (UserActions.log_date.between(dt_from, dt_to)))
        return await self._session.scalars(query)

    async def autolog_lesson(self, for_time: datetime):
        from_time = for_time - timedelta(hours=1, minutes=15)
        to_time = for_time - timedelta(minutes=15)
        query = select(ScheduleRecord)\
            .where(ScheduleRecord.absolute_start_time.between(from_time, to_time) & is_active(ScheduleRecord))\
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

        if len(users_to_check) > 1:
            user_names = [(user.id, user.fullname) for user in users_to_check]
            await self._users.send_text_message_to_admins(f"В расписании дубликаты: для учеников {user_names} "
                                                          f"была произведена попытка засчитать урок. "
                                                          f"Занеси правильный урок вручную.")
            await self._logger.error("duplicates in schedule", users=user_names)
            raise RuntimeError(f"duplicates in schedule, users={user_names}")

        await self._session.commit()
        await self._logger.info(
            "logged completed lessons",
            lessons=[{"user": lesson.user.unique_name, "lesson_start": lesson.absolute_start_time}
                     for lesson in completed_lessons]
        )

        await self._lesson_counted_notification(users_to_check)

        for user in users_to_check:
            subs = await self.count_subscriptions_on_date(user, for_time)
            one_lesson_subs = True
            non_valid_subs = 0
            for s in subs:
                one_lesson_subs &= s.is_stub or s.lessons == 1
                if s.is_exhausted() or not s.is_valid(for_time):
                    non_valid_subs += 1

            if non_valid_subs == len(subs):
                await self._users.send_text_message_to_admins(f"У ученика {user.fullname} кончился абонемент!")
                if not one_lesson_subs:
                    await self._users.send_text_message(
                        user,
                        f"Привет! Похоже, у тебя закончился абонемент 🤔\n"
                        f"Это не так? напиши Ане, разберемся.")

    async def log_subscription(
            self,
            user: User,
            template: SubscriptionTemplate,
            from_date: datetime) -> UserActions:
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
        return sub

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
            & UserActions.log_date.between(dt - timedelta(days=120), to_midnight(dt) + timedelta(days=1))
            ).order_by(UserActions.log_date)
        actions = (await self._session.scalars(query)).all()

        res = SortedList[Subscription](key=lambda x: x.valid_from)
        stub = Subscription.stub()
        for action in actions:
            if action.action_type == UserActionType.SUBSCRIPTION:
                res.add(Subscription(
                    lessons=action.subs_quantity,
                    cancellations=action.subs_cancellations,
                    valid_from=action.subs_valid_from,
                    valid_to=action.subs_valid_to
                ))

        def register_action(subs, action) -> bool:
            oldest_sub_valid_from = subs[0].valid_from if subs else datetime.min

            if action.log_date <= oldest_sub_valid_from:
                return True

            for sub in subs:
                sub: Subscription
                if not sub.is_valid(action.log_date) or sub.is_exhausted():
                    continue

                match action.action_type:
                    case UserActionType.LESSON:
                        if sub.try_add_lesson(action.log_date):
                            return True
                    case UserActionType.LESSON_CANCELLATION:
                        if sub.try_add_cancel(action.log_date):
                            return True
            return False

        for action in filter(lambda a: a.action_type != UserActionType.SUBSCRIPTION, actions):
            if not register_action(res, action):
                match action.action_type:
                    case UserActionType.LESSON:
                        stub.counted_lessons += 1
                        stub.lesson_dates.append(action.log_date)
                    case UserActionType.LESSON_CANCELLATION: stub.counted_cancellations += 1

        res.add(stub)

        return [v for v in res]

    async def _lesson_counted_notification(self, users_to_check: list[User]):
        if not users_to_check:
            return
        user = users_to_check[0]
        await self._users.send_text_message_to_admins(
            f"Прошёл и посчитан урок у ученика {user.fullname}."
        )
        pass
