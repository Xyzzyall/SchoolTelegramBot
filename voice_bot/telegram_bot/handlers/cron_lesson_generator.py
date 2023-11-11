import structlog
from injector import inject
from telegram.ext import ContextTypes

from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.spreadsheet_dumper import SpreadsheetDumper
from voice_bot.domain.services.spreadsheet_sync_service import SpreadsheetSyncService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.datetime_service import DatetimeService, dt_fmt_rus
from voice_bot.telegram_bot.base_handler import BaseScheduleHandler
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CronLessonGenerator(BaseScheduleHandler):
    @inject
    def __init__(self,
                 schedule: ScheduleService,
                 dt: DatetimeService,
                 session: UpdateSession,
                 users: UsersService,
                 dumper: SpreadsheetDumper,
                 sync: SpreadsheetSyncService):
        self.sync = sync
        self.dumper = dumper
        self.users = users
        self.session = session.session
        self.dt = dt
        self.schedule = schedule

    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.sync.sync_only_users()

            now = self.dt.now()
            elder = await self.schedule.clean_up_elder_lessons(now)
            new = await self.schedule.create_lessons_from_std_schedule(now)

            if elder + len(new) == 0:
                await self.dumper.dump_schedule()
                return

            await self.session.commit()
            await self.users.send_text_message_to_admins(f"Расписание актуализировано на {dt_fmt_rus(now)}, "
                                                         f"создано {len(new)} уроков на основе еженедельного шаблона")
            await self.dumper.dump_schedule()
            await self.users.send_text_message_to_admins("Актуализированное расписание успешно записано в гугл-таблицы")
        except Exception as e:
            await self.users.send_text_message_to_admins("Произошла ошибка при актуализации расписания. "
                                                         "Напиши моему создателю, пускай порадуется!💩"
                                                         f"\n\np.s. непонятные слова: {e.__class__} {e}")
            raise e
