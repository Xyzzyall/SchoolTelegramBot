from datetime import timedelta
from typing import Callable

import structlog
from injector import inject

from voice_bot.constants import REMINDERS_OPTIONS
from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.spreadsheets.misc import simple_cache
from voice_bot.spreadsheets.misc.simple_cache import simplecache
from voice_bot.spreadsheets.models.user import User
from voice_bot.spreadsheets.users_table import UsersTable


class GoogleUsersTable(UsersTable):
    @inject
    def __init__(self, gspread: GspreadClient):
        self._gspread = gspread
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    _TABLE_CACHE_KEY = "google_users"

    def delete_cache(self):
        simple_cache.delete_key(self._TABLE_CACHE_KEY)

    @simplecache(_TABLE_CACHE_KEY, timedelta(days=365))
    async def _fetch_users_table(self) -> list[User]:
        cells = self._gspread.gs_settings_sheet.worksheet("Ученики").get_values()
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
            if not subtext:
                continue
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

    async def get_user(self, filter_lambda: Callable[[User], bool]) -> User | None:
        users = await self.get_users()
        filtered = list(filter(filter_lambda, users))
        if len(filtered) > 1 or len(filtered) == 0:
            return None
        return filtered[0]

    async def get_users(self) -> list[User]:
        return await self._fetch_users_table()

    async def rewrite_user(self, user: User):
        real_row = user.row_id + 3
        self._gspread.gs_settings_sheet.worksheet("Ученики").batch_update(
            [{
                'range': f'A{real_row}:F{real_row}',
                'values': [[user.unique_id, user.fullname, user.telegram_login, user.secret_code, '',
                            self._timedeltas_to_cell(user.schedule_reminders)]],
            }]
        )
        self.delete_cache()
