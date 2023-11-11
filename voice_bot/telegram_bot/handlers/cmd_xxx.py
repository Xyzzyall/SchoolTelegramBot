from datetime import timedelta, datetime

from injector import inject
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.roles import UserRoles
from voice_bot.domain.services.actions_logger import ActionsLoggerService
from voice_bot.domain.services.book_lesson_service import BookLessonsService
from voice_bot.domain.services.cache_service import CacheService
from voice_bot.domain.services.reminders_service import RemindersService
from voice_bot.domain.services.schedule_service import ScheduleService
from voice_bot.domain.services.spreadsheet_sync_service import SpreadsheetSyncService
from voice_bot.domain.services.users_service import UsersService
from voice_bot.misc.user_mock import clear_mock, mock_user
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.navigation.nav_tree import REMINDER_TREE
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CmdXxx(BaseUpdateHandler):
    @inject
    def __init__(self,
                 users: UsersService,
                 sync: SpreadsheetSyncService,
                 cache: CacheService,
                 reminders: RemindersService,
                 schedule: ScheduleService,
                 log: ActionsLoggerService,
                 session: UpdateSession,
                 book: BookLessonsService):
        self.book = book
        self._session = session.session
        self._log = log
        self._schedule = schedule
        self._reminders = reminders
        self._cache = cache
        self._sync = sync
        self._users = users

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.username != 'xyzzyall':
            await update.effective_message.reply_text("💩")
            return

        if len(context.args) == 0:
            await update.effective_message.reply_text("мне ваще-то нужна команда 🙄")
            return

        match context.args[0]:
            case "sync": await self._perform_sync(update)
            case "day_reminders": await self._turn_on_day_reminders(update)
            case "spam": await self._users.send_text_message_to_roles(
                " ".join(context.args[1:]), {UserRoles.sysadmin}, send_as_is=True)
            case "test_cancel": await self._users.send_menu_to_user("242173251", REMINDER_TREE, {
                "user_id": int(context.args[1]),
                "lesson_id": int(context.args[2]),
                "reminder_timedelta": timedelta(hours=27)
            })
            case "reminders":
                res = []
                for r in await self._reminders.get_fired_reminders_at(datetime.fromisoformat(" ".join(context.args[1:]))):
                    user = await self._users.get_user_by_id(r.user_id)
                    lesson = await self._schedule.get_lesson_by_id(r.lesson_id)
                    res.append(f"{user.fullname} -- {lesson.absolute_start_time.isoformat()}")
                if len(res) == 0:
                    await update.effective_message.reply_text("нету")
                else:
                    await update.effective_message.reply_text("\n".join(res))
            case "mock":
                i = int(context.args[1])
                if i == 0:
                    clear_mock()
                    await update.effective_message.reply_text("теперь ты снова ты")
                else:
                    usr = await self._users.get_user_by_id(i)
                    mock_user(str(update.effective_user.id), usr)
                    await update.effective_message.reply_text(f"ухуху! теперь ты {usr.fullname}!")
            case "subs":
                report = []
                users = {user.unique_name: user for user in await self._users.get_all_regular_users()}
                for line in update.effective_message.text.split('\n')[1:]:
                    sub = line.split("!")
                    if len(sub) != 2:
                        report.append(f"не понел '{line}' ето шо?")
                        continue
                    un = sub[0]

                    if un not in users:
                        report.append(f"user not found {un}")
                        continue
                    user = users[un]

                    l_info = sub[1].split('/')
                    if len(l_info) != 2:
                        report.append(f"не то чето в уроках '{line}'")
                        continue
                    l0, l1 = int(l_info[0]), int(l_info[1])
                    if not self._log.migrate_subscription_and_lessons(user, l0, l1):
                        report.append(f"ну нету такого абонемента '{line}'")
                        continue
                    report.append(f"сделали по красоте '{line}'")
                await self._session.commit()
                await update.effective_message.reply_text("вот так вот добавляли абонементы:\n" + "\n".join(report))
            case "frees":
                weekday = int(context.args[1])
                from_hour = int(context.args[2])
                to_hour = int(context.args[3])
                for i in range(from_hour, to_hour):
                    await self.book.create_free_lesson(weekday, f"{i:02d}:00", f"{i:02d}:50")
                await update.effective_message.reply_text("\n".join(await self._free_lessons_report_lines(weekday)))
            case _: await update.effective_message.reply_text(f"не нашел такой команды: {context.args[0]}")

    async def _free_lessons_report_lines(self, weekday) -> list[str]:
        report = []
        for free in (await self.book.get_free_lessons_weekday(weekday)).values():
            report.append(f"free_lesson(start:{free.time_start}, end:{free.time_end})")
        return report

    async def _perform_sync(self, update: Update):
        self._cache.clear_all_cache()
        await self._sync.sync_only_users()
        await update.effective_message.reply_text("готово")

    async def _turn_on_day_reminders(self, update: Update):
        users = await self._users.get_all_regular_users()
        for user in users:
            await self._reminders.set_reminder_state_for(user, "за сутки", True)
        await update.effective_message.reply_text("готово")
