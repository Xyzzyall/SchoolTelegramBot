from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.db.enums import ScheduleRecordType
from voice_bot.db.models import User, ScheduleRecord, StandardScheduleRecord
from voice_bot.spreadsheets.params_table import ParamsTableService
from voice_bot.spreadsheets.users_table import UsersTableService
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class MessageBuilder:
    @inject
    def __init__(self, params: ParamsTableService, users: UsersTableService):
        self._users = users
        self._params = params
        self._context = dict[str, str]()

    def push(self, key: str, val: str):
        self._context[key] = val

    def push_user(self, user: User):
        self.push("ученик_фио", user.fullname)
        self.push("ученик_идентификатор", user.unique_name)
        self.push("ученик_логин", user.telegram_login)

    def push_schedule_record(self, schedule_record: ScheduleRecord | StandardScheduleRecord):
        if isinstance(schedule_record, ScheduleRecord):
            self.push_schedule(schedule_record)
        else:
            self.push_std_schedule(schedule_record)

    def push_std_schedule(self, record: StandardScheduleRecord):
        self.push("занятие_время", f"с {record.time_start} до {record.time_end}")
        self.push("занятие_время_начала", record.time_start)
        self.push("занятие_время_конца", record.time_end)
        self.push("занятие_онлайн_или_очное", self._decode_schedule_type(record.type))
        self.push("занятие_день_недели", DAYS_OF_THE_WEEK[record.day_of_the_week + 1])

    def push_schedule(self, record: ScheduleRecord):
        self.push("занятие_время", f"с {record.time_start} до {record.time_end}")
        self.push("занятие_время_начала", record.time_start)
        self.push("занятие_время_конца", record.time_end)
        self.push("занятие_онлайн_или_очное", self._decode_schedule_type(record.type))
        self.push("занятие_день_недели", DAYS_OF_THE_WEEK[record.absolute_start_time.weekday() + 1])
        self.push(
            "занятие_дата",
            record.absolute_start_time.strftime("%d.%m.%Y")
        )

    @staticmethod
    def _decode_schedule_type(t: ScheduleRecordType) -> str:
        match t:
            case ScheduleRecordType.ONLINE:
                return "онлайн"
            case ScheduleRecordType.OFFLINE:
                return "очное"
            case ScheduleRecordType.RENT:
                return "аренда"
        return ""

    async def format(self, template: str) -> str:
        return await self._params.map_template(template, **self._context)
