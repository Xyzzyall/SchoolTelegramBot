from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.spreadsheets.models.schedule_record import ScheduleRecord
from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.params_table import ParamsTable
from voice_bot.spreadsheets.users_table import UsersTable
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class MessageBuilder:
    @inject
    def __init__(self, params: ParamsTable, users: UsersTable):
        self._users = users
        self._params = params
        self._context = dict[str, str]()

    def push(self, key: str, val: str):
        self._context[key] = val

    def push_user(self, user: User):
        self.push("ученик_фио", user.fullname)
        self.push("ученик_идентификатор", user.unique_id)
        self.push("ученик_логин", user.telegram_login)

    def push_schedule_record(self, schedule_record: ScheduleRecord):
        self.push("занятие_время", f"с {schedule_record.time_start} до {schedule_record.time_end}")
        self.push("занятие_время_начала", schedule_record.time_start)
        self.push("занятие_время_конца", schedule_record.time_end)
        self.push("занятие_онлайн_или_очное", "онлайн" if schedule_record.is_online else "очное")
        self.push("занятие_день_недели", DAYS_OF_THE_WEEK[schedule_record.day_of_the_week])
        self.push(
            "занятие_дата",
            schedule_record.absolute_start_date.strftime("%d.%m.%Y") if schedule_record.absolute_start_date else ""
        )

    async def format(self, template: str) -> str:
        return await self._params.map_template(template, **self._context)
