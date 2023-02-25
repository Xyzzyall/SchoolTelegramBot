from datetime import timedelta
from typing import Callable

import structlog
from injector import inject

from voice_bot.constants import REMINDERS_OPTIONS
from voice_bot.domain.roles import BotRoles
from voice_bot.misc import simple_cache
from voice_bot.misc.simple_cache import simplecache
from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.spreadsheets.models.spreadsheet_user import SpreadsheetUser
from voice_bot.spreadsheets.users_table import UsersTableService


class GoogleUsersTableService(UsersTableService):
    @inject
    def __init__(self, gspread: GspreadClient):
        self._gspread = gspread
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    _TABLE_CACHE_KEY = "google_users"

    @staticmethod
    def delete_cache():
        simple_cache.delete_key(self._TABLE_CACHE_KEY)

    _USER_LAYOUT = {
        "Уникальное имя": "unique_id",
        "ФИО": "fullname",
        "Логин Телеграм": "telegram_login",
        "Кодовое слово": "secret_code"
    }

    def _parse_layout(self, head_rows: list[list[str]]) -> dict[str, int]:
        res: dict[str, int] = {}

        roles_column_start = head_rows[0].index("Роли")

        for i, cell in enumerate(head_rows[1][:roles_column_start+1]):
            if cell not in self._USER_LAYOUT:
                continue

            res[self._USER_LAYOUT[cell]] = i

        for i, cell in enumerate(head_rows[1][roles_column_start:]):
            if cell not in BotRoles.user_roles_names:
                continue

            res['role.' + BotRoles.user_roles_names[cell]] = i + roles_column_start

        return res

    async def _fetch_users_table_nocache(self) -> (dict[str, int], list[SpreadsheetUser]):
        cells = (await self._gspread.get_settings_worksheet("Ученики")).get_values()

        users = list[SpreadsheetUser]()

        layout = self._parse_layout(cells[:2])

        for i, row in enumerate(cells[2:]):
            if not row[layout["unique_id"]]:
                continue

            new_user = SpreadsheetUser(
                row_id=i,
                unique_id=row[layout["unique_id"]],
                fullname=row[layout["fullname"]],
                telegram_login=row[layout["telegram_login"]],
                secret_code=row[layout["secret_code"]],
                schedule_reminders=set()
                #schedule_reminders=await self._parse_schedule_reminders(row[_last_layout["schedule_reminders"]]),
                #chat_id=row[_last_layout["chat_id"]],
            )

            for key in filter(lambda k: k.startswith("role."), layout):
                if row[layout[key]] != "Да":
                    continue

                new_user.roles.append(key[len("role."):])

            users.append(new_user)

        return layout, users

    @simplecache(_TABLE_CACHE_KEY, timedelta(days=365))
    async def _fetch_users_table(self) -> list[SpreadsheetUser]:
        _, users = await self._fetch_users_table_nocache()
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

    async def get_user(self, filter_lambda: Callable[[SpreadsheetUser], bool]) -> SpreadsheetUser | None:
        users = await self.get_users()

        filtered = list(filter(filter_lambda, users))
        if len(filtered) > 1 or len(filtered) == 0:
            return None

        return filtered[0]

    async def get_users(self) -> list[SpreadsheetUser]:
        return await self._fetch_users_table()

    async def rewrite_user(self, user: SpreadsheetUser):
        layout, users_reloaded = await self._fetch_users_table_nocache()
        reloaded_user = next(filter(lambda x: x.unique_id == user.unique_id, users_reloaded))

        real_row = reloaded_user.row_id + 3
        resulting_array = self._to_table_row(layout, user)

        self._gspread.gs_settings_sheet.worksheet("Ученики").batch_update(
            [{
                'range': f'A{real_row}:Z{real_row}',
                'values': [resulting_array],
            }]
        )

        self.delete_cache()

    def _to_table_row(self, layout, user):
        resulting_array = 26 * ['']
        resulting_array[layout["unique_id"]] = user.unique_id
        resulting_array[layout["fullname"]] = user.fullname
        resulting_array[layout["telegram_login"]] = user.telegram_login
        resulting_array[layout["secret_code"]] = user.secret_code
        #resulting_array[layout["schedule_reminders"]] = self._timedeltas_to_cell(user.schedule_reminders)
        #resulting_array[layout["chat_id"]] = user.chat_id

        for key in BotRoles.user_roles:
            if key in user.roles:
                resulting_array[layout["role." + key]] = "Да"

        return resulting_array

    _last_layout = None

    async def dump_records(self, **kwargs) -> list[SpreadsheetUser]:
        layout, users = await self._fetch_users_table_nocache()
        self._last_layout = layout
        return users

    async def rewrite_all_records(self, records: list[SpreadsheetUser]):
        records.sort(key=lambda x: x.unique_id)

        rows = [self._to_table_row(self._last_layout, user) for user in filter(lambda x: not x.to_delete, records)]

        worksheet = await self._gspread.get_settings_worksheet("Ученики")

        worksheet.batch_update(
            [{
                'range': f'A3:Z{len(rows) + 2}',
                'values': rows,
            }]
        )
