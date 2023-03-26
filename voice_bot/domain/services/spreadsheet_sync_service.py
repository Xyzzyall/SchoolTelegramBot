from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import chain

import structlog
from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import joinedload, subqueryload
from typing_extensions import override

from voice_bot.db.enums import DumpStates, ScheduleRecordType, YesNo
from voice_bot.db.models import User, StandardScheduleRecord, ScheduleRecord, UserRole
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.alarm_service import AlarmService
from voice_bot.domain.services.cache_service import CacheService
from voice_bot.misc.datetime_service import DatetimeService
from voice_bot.spreadsheets.admins_table import AdminsTableService
from voice_bot.spreadsheets.models.spreadsheet_admin import SpreadsheetAdmin
from voice_bot.spreadsheets.models.spreadsheet_schedule_record import SpreadsheetScheduleRecord
from voice_bot.spreadsheets.models.spreadsheet_user import SpreadsheetUser
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.spreadsheets.schedule_table import ScheduleTableService
from voice_bot.spreadsheets.tables_service import TablesService
from voice_bot.spreadsheets.users_table import UsersTableService
from voice_bot.telegram_di_scope import telegramupdate

_ALL_USERS_STMT = select(User).options(subqueryload(User.roles))
_ALL_STD_SCHEDULE_STMT = select(StandardScheduleRecord).options(joinedload(StandardScheduleRecord.user))
_ALL_SCHEDULE_STMT = select(ScheduleRecord).options(joinedload(ScheduleRecord.user))


@dataclass
class _UserDto:
    unique_name: str
    is_admin: bool = False
    fullname: str = None
    secret_code: str = None
    roles: list[str] = None
    telegram_login: str = None
    bot_record: User = None


@dataclass
class _ScheduleDto:
    user_unique_name: str
    weekday: int
    start_time: str
    end_time: str
    absolute_start: datetime | None
    is_online: bool = False
    bot_record: ScheduleRecord = None
    bot_std_record: StandardScheduleRecord = None
    to_delete_in_bot: bool = False
    to_delete_in_table: bool = False

    def short_str(self):
        return f"<{self.user_unique_name}, delete?{self.to_delete_in_table or self.to_delete_in_bot}>"


@telegramupdate
class SpreadsheetSyncService:
    @inject
    def __init__(self,
                 users_table: UsersTableService,
                 session: UpdateSession,
                 admins_table: AdminsTableService,
                 schedule_table: ScheduleTableService,
                 params_table: ParamsTableService,
                 tables: TablesService,
                 cache: CacheService,
                 alarm: AlarmService,
                 dt: DatetimeService):
        self._dt = dt
        self._alarm = alarm
        self._cache = cache
        self._tables = tables
        self._params = params_table
        self._schedule_table = schedule_table
        self._admins = admins_table
        self._users = users_table
        self._session = session()
        self._logger = structlog.get_logger(class_name=__class__.__name__)

        self._table_users: list[SpreadsheetUser] = []
        self._table_admins: list[SpreadsheetAdmin] = []
        self._table_schedule: list[SpreadsheetScheduleRecord] = []
        self._bot_users: list[User] = []
        self._bot_schedule: list[ScheduleRecord] = []
        self._bot_std_schedule: list[StandardScheduleRecord] = []

        self._users_merge: dict[str, _UserDto] = {}
        self._schedule_merge: dict[str, _ScheduleDto] = {}

    async def perform_sync(self):
        self._users_merge = {}
        self._schedule_merge = {}

        self._table_users = await self._users.dump_records()
        self._table_admins = await self._admins.dump_records()
        self._bot_users = (await self._session.scalars(_ALL_USERS_STMT)).all()
        await self._sync_users()

        await self._tables.create_tables_if_not_exist()
        self._bot_schedule = (await self._session.scalars(_ALL_SCHEDULE_STMT)).all()
        self._bot_std_schedule = (await self._session.scalars(_ALL_STD_SCHEDULE_STMT)).all()
        self._table_schedule = await self._dump_schedule()
        await self._sync_schedule()

        await self._session.commit()
        await self._users.rewrite_all_records(self._table_users)
        await self._admins.rewrite_all_records(self._table_admins)
        await self._schedule_table.rewrite_all_records(self._merged_schedule_to_table())
        self._cache.clear_claims_cache()

    async def _dump_schedule(self) -> list[SpreadsheetScheduleRecord]:
        now = self._dt.now()
        current_monday = now - timedelta(days=now.weekday())
        return await self._schedule_table.dump_records(
            from_monday=current_monday,
            weeks=int(await self._params.get_param("расписание_недель_вперёд")) + 1
        )

    async def _sync_users(self):
        for record in chain(self._table_users, self._table_admins, self._bot_users):
            if isinstance(record, SpreadsheetUser):
                user = _UserDto(record.unique_id)
                user.is_admin = False
                user.secret_code = record.secret_code
                user.fullname = record.fullname
                user.roles = record.roles
                self._users_merge[record.unique_id] = user
                continue

            if isinstance(record, SpreadsheetAdmin):
                user = _UserDto(record.unique_id)
                user.is_admin = True
                user.secret_code = record.secret_code
                user.fullname = record.fullname
                user.roles = record.roles
                self._users_merge[record.unique_id] = user
                continue

            record: User
            if record.unique_name in self._users_merge:
                user = self._users_merge[record.unique_name]
                user.bot_record = record
                self._sync_bot_user(record, user)
                continue

            await self._session.delete(record)

        for new_user in filter(lambda u: not u.bot_record, self._users_merge.values()):
            new_user: _UserDto
            user = User(
                unique_name=new_user.unique_name,
                fullname=new_user.fullname,
                secret_code=new_user.secret_code,
                is_admin=YesNo.YES if new_user.is_admin else YesNo.NO,
                dump_state=DumpStates.ACTIVE,
            )
            user.roles = [UserRole(user=user, role_name=role) for role in new_user.roles]
            for role in user.roles:
                self._session.add(role)
            self._session.add(user)
            new_user.bot_record = user

        for table_user in self._table_users:
            dto = self._users_merge[table_user.unique_id]
            table_user.telegram_login = dto.telegram_login

        for table_admin in self._table_admins:
            dto = self._users_merge[table_admin.unique_id]
            table_admin.telegram_login = dto.telegram_login

    def _sync_bot_user(self, bot_user: User, dto: _UserDto):
        bot_user.fullname = dto.fullname
        bot_user.secret_code = dto.secret_code
        dto.telegram_login = bot_user.telegram_login

        bot_roles = {role.role_name: role for role in bot_user.roles}
        new_bot_roles = []
        for table_role in dto.roles:
            if table_role in bot_roles:
                new_bot_roles.append(bot_roles[table_role])
                continue

            new_role = UserRole(user=bot_user, role_name=table_role)
            self._session.add(new_role)
            new_bot_roles.append(new_role)

        bot_user.roles = new_bot_roles

    async def _sync_schedule(self):
        await self._logger.info(
            "got table schedule",
            table=", ".join([f"{rec.table_name}/{rec.day_of_the_week}/{rec.raw_time_start_time_end}/{rec.user_id}"
                             for rec in self._table_schedule]))

        for table_record in self._table_schedule:
            key = self._generate_str_schedule_key_for_table(table_record)
            schedule = _ScheduleDto(
                user_unique_name=table_record.user_id,
                start_time=table_record.time_start,
                end_time=table_record.time_end,
                weekday=table_record.day_of_the_week - 1,
                absolute_start=table_record.absolute_start_time,
                is_online=table_record.is_online
            )
            self._schedule_merge[key] = schedule

        await self._logger.info(
            "dumped table schedule",
            vals=", ".join([f"'{k}':{v.short_str()}" for k, v in self._schedule_merge.items()]))

        for record in chain(self._bot_std_schedule, self._bot_schedule):
            key = self._generate_str_schedule_key(record)
            if isinstance(record, ScheduleRecord):
                record: ScheduleRecord
                schedule = self._schedule_merge[key] if key in self._schedule_merge else _ScheduleDto(
                    user_unique_name=record.user.unique_name,
                    absolute_start=record.absolute_start_time,
                    start_time=record.time_start,
                    end_time=record.time_end,
                    weekday=-1,
                    is_online=record.type == ScheduleRecordType.ONLINE,
                    to_delete_in_bot=record.dump_state != DumpStates.TO_SYNC,
                    to_delete_in_table=record.dump_state != DumpStates.TO_SYNC,
                )
                schedule.bot_record = record
            else:
                record: StandardScheduleRecord
                schedule = self._schedule_merge[key] if key in self._schedule_merge else _ScheduleDto(
                    user_unique_name=record.user.unique_name,
                    absolute_start=None,
                    start_time=record.time_start,
                    end_time=record.time_end,
                    weekday=record.day_of_the_week,
                    is_online=record.type == ScheduleRecordType.ONLINE,
                    to_delete_in_bot=record.dump_state != DumpStates.TO_SYNC,
                    to_delete_in_table=record.dump_state != DumpStates.TO_SYNC,
                )
                schedule.bot_std_record = record
            self._schedule_merge[key] = schedule

            if schedule.user_unique_name not in self._users_merge:
                await self._logger.warning(
                    "sync: cannot find user in user's table", user=schedule.user_unique_name, key=key)
                schedule.to_delete_in_bot = True
                schedule.to_delete_in_table = True
                continue

            if schedule.user_unique_name != record.user.unique_name:
                record.user = self._users_merge[schedule.user_unique_name].bot_record
                record.dump_state = DumpStates.ACTIVE
                record.type = ScheduleRecordType.ONLINE if schedule.is_online else ScheduleRecordType.OFFLINE
                continue

            schedule.to_delete_in_table = schedule.to_delete_in_table or record.dump_state == DumpStates.BOT_DELETED
            schedule.to_delete_in_bot = schedule.to_delete_in_bot or record.dump_state == DumpStates.BOT_DELETED

        await self._logger.info(
            "merging schedule", vals=", ".join([f"'{k}':{v.short_str()}" for k, v in self._schedule_merge.items()]))

        for merged_record in self._schedule_merge.values():
            if merged_record.to_delete_in_bot and (merged_record.bot_record or merged_record.bot_std_record):
                await self._session.delete(merged_record.bot_record or merged_record.bot_std_record)
                continue

            if not merged_record.bot_record and not merged_record.bot_std_record:
                if merged_record.user_unique_name not in self._users_merge:
                    await self._alarm.warning(
                        "В расписании есть имена, которых нет в таблице учеников. Может быть опечатка?",
                        src=SpreadsheetSyncService,
                        name=merged_record.user_unique_name,
                    )
                    continue

                if not merged_record.absolute_start:
                    new_record = StandardScheduleRecord(
                        user=self._users_merge[merged_record.user_unique_name].bot_record,
                        day_of_the_week=merged_record.weekday,
                        time_start=merged_record.start_time,
                        time_end=merged_record.end_time,
                        type=ScheduleRecordType.ONLINE if merged_record.is_online else ScheduleRecordType.OFFLINE,
                        dump_state=DumpStates.ACTIVE,
                    )
                    merged_record.bot_std_record = new_record
                else:
                    new_record = ScheduleRecord(
                        user=self._users_merge[merged_record.user_unique_name].bot_record,
                        absolute_start_time=merged_record.absolute_start,
                        time_start=merged_record.start_time,
                        time_end=merged_record.end_time,
                        type=ScheduleRecordType.ONLINE if merged_record.is_online else ScheduleRecordType.OFFLINE,
                        dump_state=DumpStates.ACTIVE
                    )
                    merged_record.bot_record = new_record
                self._session.add(new_record)

    def _merged_schedule_to_table(self) -> list[SpreadsheetScheduleRecord]:
        res: list[SpreadsheetScheduleRecord] = []
        for merged in self._schedule_merge.values():
            if merged.to_delete_in_table:
                continue
            res.append(SpreadsheetScheduleRecord(
                table_name=None,
                is_online=merged.is_online,
                day_of_the_week=merged.weekday + 1,
                time_start=merged.start_time,
                time_end=merged.end_time,
                to_delete=False,
                absolute_start_time=merged.absolute_start,
                user_id=merged.user_unique_name,
                raw_time_start_time_end=f'{merged.start_time}-{merged.end_time}'
            ))
        return res

    @staticmethod
    def _generate_str_schedule_key_for_table(schedule: SpreadsheetScheduleRecord):
        if schedule.absolute_start_time and schedule.table_name != "Стандарт":
            return f"{schedule.absolute_start_time.isoformat()}"

        return f"{schedule.day_of_the_week - 1};{schedule.time_start}-{schedule.time_end}"

    @staticmethod
    def _generate_str_schedule_key(
            schedule: ScheduleRecord | StandardScheduleRecord
    ) -> str:
        if isinstance(schedule, ScheduleRecord):
            return f"{schedule.absolute_start_time.isoformat()}"

        if isinstance(schedule, StandardScheduleRecord):
            return f"{schedule.day_of_the_week};{schedule.time_start}-{schedule.time_end}"

        raise RuntimeError()
