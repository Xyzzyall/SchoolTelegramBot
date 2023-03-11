from injector import singleton, inject

from voice_bot.domain.roles import BotRoles
from voice_bot.spreadsheets.admins_table import AdminsTableService
from voice_bot.spreadsheets.google_cloud.gspread import GspreadClient
from voice_bot.spreadsheets.models.spreadsheet_admin import SpreadsheetAdmin


@singleton
class GoogleAdminsTableService(AdminsTableService):
    @inject
    def __init__(self, gspread: GspreadClient):
        self._gspread = gspread

    async def get_admin(self, telegram_login: str) -> SpreadsheetAdmin:
        pass

    _ADMIN_LAYOUT = {
        "Уникальное имя": "unique_id",
        "ФИО": "fullname",
        "Логин Телеграм": "telegram_login",
        "Кодовое слово": "secret_code"
    }

    def _parse_layout(self, head_rows: list[list[str]]) -> dict[str, int]:
        res: dict[str, int] = {}

        roles_column_start = head_rows[0].index("Роли")

        for i, cell in enumerate(head_rows[1][:roles_column_start+1]):
            if cell not in self._ADMIN_LAYOUT:
                continue

            res[self._ADMIN_LAYOUT[cell]] = i

        for i, cell in enumerate(head_rows[1][roles_column_start:]):
            if cell not in BotRoles.admin_roles_names:
                continue

            res['role.' + BotRoles.admin_roles_names[cell]] = i + roles_column_start

        return res

    async def _fetch(self) -> (dict[str, int], list[SpreadsheetAdmin]):
        worksheet = await self._gspread.get_settings_worksheet("Админы")
        values = worksheet.get_values()

        res = []

        layout = self._parse_layout(values[:2])

        for i, row in enumerate(values[2:]):
            if not row[layout["unique_id"]]:
                continue

            new_admin = SpreadsheetAdmin(
                unique_id=row[layout["unique_id"]],
                fullname=row[layout["fullname"]],
                telegram_login=row[layout["telegram_login"]],
                secret_code=row[layout["secret_code"]],
            )

            for key in filter(lambda k: k.startswith("role."), layout):
                if row[layout[key]] != "Да":
                    continue

                new_admin.roles.append(key[len("role."):])

            res.append(new_admin)

        return layout, res

    _last_layout: dict[str, int] = {}

    async def dump_records(self, **kwargs) -> list[SpreadsheetAdmin]:
        layout, records = await self._fetch()
        self._last_layout = layout
        return records

    def _to_table_row(self, admin: SpreadsheetAdmin) -> list[str]:
        resulting_array = 26 * ['']
        resulting_array[self._last_layout["unique_id"]] = admin.unique_id
        resulting_array[self._last_layout["fullname"]] = admin.fullname
        resulting_array[self._last_layout["telegram_login"]] = admin.telegram_login
        resulting_array[self._last_layout["secret_code"]] = admin.secret_code

        for key in BotRoles.admin_roles:
            if key in admin.roles:
                resulting_array[self._last_layout["role." + key]] = "Да"

        return resulting_array

    async def rewrite_all_records(self, records: list[SpreadsheetAdmin]):
        records.sort(key=lambda x: x.unique_id)

        rows = [self._to_table_row(admin) for admin in filter(lambda x: not x.to_delete, records)]

        worksheet = await self._gspread.get_settings_worksheet("Админы")

        worksheet.batch_update(
            [{
                'range': f'A3:Z{len(rows) + 2}',
                'values': rows,
            }, {
                'range': f'A{len(rows) + 3}:Z1000',
                'values': (1000 - len(rows) - 2) * [26 * ['']]
            }]
        )

    @staticmethod
    def delete_cache():
        pass

