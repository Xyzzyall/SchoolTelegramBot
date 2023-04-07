from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from voice_bot.db.base_model import BaseModel
from voice_bot.db.enums import ScheduleRecordType, DumpStates, YesNo


class User(BaseModel):
    __tablename__ = "USERS"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    unique_name: Mapped[str] = mapped_column(String(30), unique=True)
    fullname: Mapped[str] = mapped_column(String(200))

    secret_code: Mapped[Optional[str]] = mapped_column(String(60))

    telegram_login: Mapped[Optional[str]] = mapped_column(String(60), init=False)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(20), init=False)

    is_admin: Mapped[YesNo] = mapped_column(Enum(YesNo))

    reminders: Mapped[List["UserLessonReminder"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", init=False
    )

    roles: Mapped[List["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", init=False
    )

    comments: Mapped[List["UserComment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="UserComment.user_id", init=False
    )

    std_lessons: Mapped[List["StandardScheduleRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", init=False
    )
    lessons: Mapped[List["ScheduleRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", init=False
    )

    dump_state: Mapped[DumpStates] = mapped_column(Enum(DumpStates))
    updated_on: Mapped[datetime] = mapped_column(onupdate=datetime.now, default_factory=datetime.now)
    created_on: Mapped[datetime] = mapped_column(default_factory=datetime.now)


class UserLessonReminder(BaseModel):
    __tablename__ = "USERS_REMINDERS"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"), init=False)
    user: Mapped["User"] = relationship(
        back_populates="reminders"
    )

    remind_minutes_before: Mapped[int]
    is_active: Mapped[YesNo] = mapped_column(Enum(YesNo))


class UserRole(BaseModel):
    __tablename__ = "USERS_ROLES"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"), init=False)
    user: Mapped["User"] = relationship(
        back_populates="roles"
    )

    role_name: Mapped[str] = mapped_column(String(60))


class UserComment(BaseModel):
    __tablename__ = "USERS_COMMENTS"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"), init=False)
    user: Mapped["User"] = relationship(
        back_populates="comments", foreign_keys=[user_id]
    )

    text: Mapped[str] = mapped_column(String(1000))

    created_by_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"))
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class StandardScheduleRecord(BaseModel):
    __tablename__ = "STD_SCHEDULE"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    user: Mapped["User"] = relationship(
        back_populates="std_lessons"
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"), init=False)

    day_of_the_week: Mapped[int]
    time_start: Mapped[str] = mapped_column(String(16))
    time_end: Mapped[str] = mapped_column(String(16))

    type: Mapped[ScheduleRecordType] = mapped_column(Enum(ScheduleRecordType))

    location: Mapped[Optional[str]] = mapped_column(String(128), init=False)  # todo: for future usage

    dump_state: Mapped[DumpStates] = mapped_column(Enum(DumpStates))
    updated_on: Mapped[datetime] = mapped_column(onupdate=datetime.now, default_factory=datetime.now)
    created_on: Mapped[datetime] = mapped_column(default_factory=datetime.now)


class ScheduleRecord(BaseModel):
    __tablename__ = "SCHEDULE"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    user: Mapped["User"] = relationship(
        back_populates="lessons"
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"), init=False)

    absolute_start_time: Mapped[datetime]
    time_start: Mapped[str] = mapped_column(String(16))
    time_end: Mapped[str] = mapped_column(String(16))

    type: Mapped[ScheduleRecordType] = mapped_column(Enum(ScheduleRecordType))

    location: Mapped[Optional[str]] = mapped_column(String(128), init=False)

    dump_state: Mapped[DumpStates] = mapped_column(Enum(DumpStates))
    updated_on: Mapped[datetime] = mapped_column(onupdate=datetime.now, default_factory=datetime.now)
    created_on: Mapped[datetime] = mapped_column(default_factory=datetime.now)

