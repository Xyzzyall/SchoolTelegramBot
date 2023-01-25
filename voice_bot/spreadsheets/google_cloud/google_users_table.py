from datetime import timedelta

import structlog
from injector import inject

from voice_bot.constants import REMINDERS_OPTIONS
from voice_bot.spreadsheets.google_cloud.gspread import gs_sheet
from voice_bot.spreadsheets.misc import simple_cache
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.users_table import UsersTable


class GoogleUsersTable(UsersTable):
    @inject
    def __init__(self):
        self._logger = structlog.get_logger(class_name=__class__.__name__)
        pass

    _TABLE_CACHE_KEY = "google_users"

    def delete_cache(self):
        simple_cache.delete_key(self._TABLE_CACHE_KEY)

    async def _rewrite_user(self, user: User):
        real_row = user.row_id + 3
        gs_sheet.worksheet("Ученики").batch_update(
            [{
                'range': f'A{real_row}:F{real_row}',
                'values': [[user.unique_id, user.fullname, user.telegram_login, user.secret_code, '',
                            self._timedeltas_to_cell(user.schedule_reminders)]],
            }]
        )
        self.delete_cache()

    @simplecache(_TABLE_CACHE_KEY, timedelta(days=365))
    async def _fetch_users_table(self) -> list[User]:
        cells = gs_sheet.worksheet("Ученики").get_values()
        users = list[User]()
        for i, row in enumerate(cells[2:]):
            if not row[0]:
                continue
            new_user = User(
                row_id=i,
                unique_id=row[0],
                fullname=row[1],
                telegram_login=None if row[2] == '' else row[2],
                secret_code=None if row[3] == '' else row[3],
                schedule_reminders=await self._parse_schedule_reminders(row[5])
            )
            users.append(new_user)
        return users

    async def _parse_schedule_reminders(self, text: str) -> set[timedelta]:
        res = set[timedelta]()
        for subtext in text.split(', '):
            key = subtext.lower()
            if key not in REMINDERS_OPTIONS:
                await self._logger.awarning("Unknown reminder option key", missing_key=key)
                continue
            res.add(REMINDERS_OPTIONS[key])
        return res

    @staticmethod
    def _timedeltas_to_cell(deltas: set[timedelta]):
        res_list = list[str]()
        for k, v in REMINDERS_OPTIONS.items():
            if v in deltas:
                res_list.append(k)
        return ', '.join(res_list)

    async def get_user(self, telegram_login: str) -> User | None:
        pass

    async def authorize_user(self, telegram_login: str, secret_word: str) -> (bool, User | None):
        if not secret_word:
            return False, None

        users = await self._fetch_users_table()
        user_with_secret = list(filter(lambda v: v.secret_code == secret_word, users))
        if len(user_with_secret) == 0:
            return False, None
        if len(user_with_secret) > 1:
            await self._logger.awarning("Duplicate secret words", secret_word=secret_word)
            return False, None

        user = user_with_secret[0]
        user.secret_code = ''
        user.telegram_login = telegram_login
        await self._rewrite_user(user)
        return True, user
