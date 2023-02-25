from datetime import datetime, timedelta

from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import joinedload, subqueryload

from voice_bot.db.enums import DumpStates, ScheduleRecordType, YesNo
from voice_bot.db.models import User, StandardScheduleRecord, ScheduleRecord, UserRole
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.cache_service import CacheService
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


@telegramupdate
class SpreadsheetSyncService:
    @inject
    def __init__(self, users_table: UsersTableService,
                 session: UpdateSession,
                 admins_table: AdminsTableService,
                 schedule_table: ScheduleTableService,
                 params_table: ParamsTableService,
                 tables: TablesService,
                 cache: CacheService):
        self._cache = cache
        self._tables = tables
        self._params = params_table
        self._schedule_table = schedule_table
        self._admins = admins_table
        self._users = users_table
        self._session = session.session

    async def perform_sync(self):
        await self._sync_users()
        await self._sync_schedule()
        self._cache.clear_claims_cache()

    async def _sync_users(self):
        bot_users = (await self._session.scalars(_ALL_USERS_STMT)).all()
        bot_users_dict: dict[str, User] = {user.unique_name: user for user in bot_users}

        table_users = await self._users.dump_records()

        for table_user in table_users:
            if table_user.unique_id not in bot_users_dict:
                self._create_user_from_table(table_user)
                continue

            user = bot_users_dict[table_user.unique_id]

            if user.is_admin == YesNo.YES:
                continue

            if user.dump_state == DumpStates.BOT_DELETED:
                table_user.to_delete = True
                self._session.delete(user)
                continue

            self._sync_table_user_and_bot_user(table_user, user)

        table_users_keys = set((user.unique_id for user in table_users))

        for bot_user in bot_users:
            if bot_user.dump_state != DumpStates.TO_SYNC or bot_user.is_admin:
                continue

            if bot_user.unique_name not in table_users_keys:
                bot_user.dump_state = DumpStates.TABLE_DELETED
                self._session.delete(bot_user)
                continue

            table_users.append(self._create_table_user_from_bot_user(bot_user))

        await self._users.rewrite_all_records(table_users)

        table_admins = await self._admins.dump_records()
        for table_admin in table_admins:
            if table_admin.unique_id not in bot_users_dict:
                self._create_user_from_table(table_admin)
                continue

            user = bot_users_dict[table_admin.unique_id]
            if user.is_admin == YesNo.NO:
                continue

            if user.dump_state == DumpStates.BOT_DELETED:
                table_admin.to_delete = True
                self._session.delete(user)
                continue

            self._sync_table_user_and_bot_user(table_admin, user)

        for bot_user in bot_users:
            if bot_user.dump_state != DumpStates.TO_SYNC or not bot_user.is_admin:
                continue

            if bot_user.unique_name not in table_users_keys:
                bot_user.dump_state = DumpStates.TABLE_DELETED
                self._session.delete(bot_user)
                continue

        await self._admins.rewrite_all_records(table_admins)

        await self._session.commit()

    def _create_user_from_table(self, user: SpreadsheetUser | SpreadsheetAdmin):
        bot_user = User(
            unique_name=user.unique_id,
            fullname=user.fullname,
            secret_code=user.secret_code,
            is_admin=YesNo.NO if isinstance(user, SpreadsheetUser) else YesNo.YES,
            dump_state=DumpStates.ACTIVE,
        )

        bot_user.roles = [UserRole(user=bot_user, role_name=role) for role in user.roles]
        for role in bot_user.roles:
            self._session.add(role)

        self._session.add(bot_user)

    def _sync_table_user_and_bot_user(self, table_user: SpreadsheetUser | SpreadsheetAdmin, bot_user: User):
        bot_user.fullname = table_user.fullname
        bot_user.secret_code = table_user.secret_code
        table_user.telegram_login = bot_user.telegram_login

        bot_roles = {role.role_name: role for role in bot_user.roles}
        new_bot_roles = []
        for table_role in table_user.roles:
            if table_role in bot_roles:
                new_bot_roles.append(bot_roles[table_role])
                continue

            new_role = UserRole(user=bot_user, role_name=table_role)
            self._session.add(new_role)
            new_bot_roles.append(new_role)

        bot_user.roles = new_bot_roles

    @staticmethod
    def _create_table_user_from_bot_user(user: User) -> SpreadsheetUser:
        user.dump_state = DumpStates.ACTIVE
        return SpreadsheetUser(
            row_id=-1,
            unique_id=user.unique_name,
            fullname=user.fullname,
            telegram_login=user.telegram_login,
            secret_code='',
            schedule_reminders=set(),
            roles=[role.role_name for role in user.roles]
        )

    async def _sync_schedule(self):
        await self._tables.create_tables_if_not_exist()

        bot_users = (await self._session.scalars(_ALL_USERS_STMT)).all()
        bot_users_dict: dict[str, User] = {user.unique_name: user for user in bot_users}

        now = datetime.now()
        current_monday = now - timedelta(days=now.weekday())

        schedule_records = await self._schedule_table.dump_records(
            from_monday=current_monday,
            weeks=int(await self._params.get_param("расписание_недель_вперёд")) + 1
        )

        await self._sync_std_schedule(schedule_records, bot_users_dict)
        await self._sync_daily_schedule(schedule_records, bot_users_dict)

        await self._schedule_table.rewrite_all_records(schedule_records)
        await self._session.commit()

    async def _sync_std_schedule(self, table_schedule_records: list[SpreadsheetScheduleRecord],
                                 bot_users_dict: dict[str, User]):
        bot_std_schedule = (await self._session.scalars(_ALL_STD_SCHEDULE_STMT)).all()

        bot_std_schedule_dict = {self._generate_str_schedule_key(record): record for record in bot_std_schedule}

        for table_schedule in filter(lambda x: not x.absolute_start_time, table_schedule_records):
            table_schedule: SpreadsheetScheduleRecord
            key = self._generate_str_schedule_key(table_schedule)

            if key not in bot_std_schedule_dict:
                self._create_std_schedule_record_from_table(table_schedule, bot_users_dict)
                continue

            bot_schedule: StandardScheduleRecord = bot_std_schedule_dict[key]

            if bot_schedule.dump_state == DumpStates.BOT_DELETED:
                table_schedule.to_delete = True
                self._session.delete(bot_schedule)
                continue

            self._sync_bot_and_table_standard_schedule(bot_schedule, table_schedule, bot_users_dict)

        for bot_schedule in bot_std_schedule:
            if bot_schedule.dump_state != DumpStates.TO_SYNC:
                continue

            table_schedule_records.append(self._create_std_schedule_table_record_from_bot(bot_schedule))

    @staticmethod
    def _determine_schedule_record_type(record: SpreadsheetScheduleRecord) -> ScheduleRecordType:  # todo add rent type
        if record.is_online:
            return ScheduleRecordType.ONLINE
        return ScheduleRecordType.OFFLINE

    def _create_std_schedule_record_from_table(self, record: SpreadsheetScheduleRecord,
                                               bot_users_dict: dict[str, User]):
        new_record = StandardScheduleRecord(
            user=bot_users_dict[record.user_id],
            day_of_the_week=record.day_of_the_week - 1,
            time_start=record.time_start,
            time_end=record.time_end,
            type=self._determine_schedule_record_type(record),
            dump_state=DumpStates.ACTIVE
        )

        self._session.add(new_record)

    def _sync_bot_and_table_standard_schedule(self, record_bot: StandardScheduleRecord,
                                              record_table: SpreadsheetScheduleRecord,
                                              bot_users_dict: dict[str, User]):
        if record_bot.dump_state == DumpStates.TO_SYNC:
            record_table.user_id = record_bot.user.unique_name
            record_table.is_online = record_bot.type == ScheduleRecordType.ONLINE
        else:
            record_bot.user = bot_users_dict[record_table.user_id]
            record_bot.type = self._determine_schedule_record_type(record_table)

        record_bot.dump_state = DumpStates.ACTIVE

    @staticmethod
    def _create_std_schedule_table_record_from_bot(record: StandardScheduleRecord) -> SpreadsheetScheduleRecord:
        record.dump_state = DumpStates.ACTIVE
        return SpreadsheetScheduleRecord(
            table_name=ScheduleTableService.STANDARD_SCHEDULE_TABLE_NAME,
            raw_time_start_time_end=f"{record.time_start}-{record.time_end}",
            is_online=record.type == ScheduleRecordType.ONLINE,
            day_of_the_week=record.day_of_the_week + 1,
            time_start='', time_end='',
            user_id=record.user.unique_name
        )

    async def _sync_daily_schedule(self, table_schedule_records: list[SpreadsheetScheduleRecord],
                                   bot_users_dict: dict[str, User]):
        bot_daily_schedule = (await self._session.scalars(_ALL_SCHEDULE_STMT)).all()

        bot_daily_schedule_dict = {self._generate_str_schedule_key(record): record for record in bot_daily_schedule}

        for table_schedule in filter(lambda x: x.absolute_start_time, table_schedule_records):
            table_schedule: SpreadsheetScheduleRecord
            key = self._generate_str_schedule_key(table_schedule)

            if key not in bot_daily_schedule_dict:
                self._create_daily_schedule_record_from_table(table_schedule, bot_users_dict)
                continue

            bot_schedule: ScheduleRecord = bot_daily_schedule_dict[key]

            if bot_schedule.dump_state == DumpStates.BOT_DELETED:
                table_schedule.to_delete = True
                self._session.delete(bot_schedule)
                continue

            self._sync_bot_and_table_daily_schedule(bot_schedule, table_schedule, bot_users_dict)

        for bot_schedule in bot_daily_schedule:
            if bot_schedule.dump_state != DumpStates.TO_SYNC:
                continue

            table_schedule_records.append(self._create_daily_schedule_table_record_from_bot(bot_schedule))

    def _create_daily_schedule_record_from_table(self, record: SpreadsheetScheduleRecord,
                                                 bot_users_dict: dict[str, User]):
        new_record = ScheduleRecord(
            user=bot_users_dict[record.user_id],
            absolute_start_time=record.absolute_start_time,
            time_start=record.time_start,
            time_end=record.time_end,
            type=self._determine_schedule_record_type(record),
            dump_state=DumpStates.ACTIVE
        )

        self._session.add(new_record)

    def _sync_bot_and_table_daily_schedule(self, record_bot: ScheduleRecord,
                                           record_table: SpreadsheetScheduleRecord,
                                           bot_users_dict: dict[str, User]):
        if record_bot.dump_state == DumpStates.TO_SYNC:
            record_table.user_id = record_bot.user.unique_name
            record_table.is_online = record_bot.type == ScheduleRecordType.ONLINE
        else:
            record_bot.user = bot_users_dict[record_table.user_id]
            record_bot.type = self._determine_schedule_record_type(record_table)

        record_bot.dump_state = DumpStates.ACTIVE

    @staticmethod
    def _create_daily_schedule_table_record_from_bot(record: ScheduleRecord) -> SpreadsheetScheduleRecord:
        record.dump_state = DumpStates.ACTIVE
        start_time: datetime = record.absolute_start_time
        return SpreadsheetScheduleRecord(
            table_name=ScheduleTableService.generate_table_name(
                start_time.date() - timedelta(days=start_time.weekday())
            ),
            raw_time_start_time_end=f"{record.time_start}-{record.time_end}",
            is_online=record.type == ScheduleRecordType.ONLINE,
            day_of_the_week=start_time.weekday(),
            time_start='', time_end='',
            user_id=record.user.unique_name
        )

    @staticmethod
    def _generate_str_schedule_key(
            schedule: SpreadsheetScheduleRecord | ScheduleRecord | StandardScheduleRecord
    ) -> str:
        if isinstance(schedule, SpreadsheetScheduleRecord):
            if schedule.absolute_start_time:
                return f"{schedule.user_id};{schedule.absolute_start_time.isoformat()}"

            return f"{schedule.user_id};{schedule.day_of_the_week-1};{schedule.time_start}-{schedule.time_end}"

        if isinstance(schedule, ScheduleRecord):
            return f"{schedule.user.unique_name};{schedule.absolute_start_time.isoformat()}"

        if isinstance(schedule, StandardScheduleRecord):
            return f"{schedule.user.unique_name};{schedule.day_of_the_week};{schedule.time_start}-{schedule.time_end}"

        raise RuntimeError()
