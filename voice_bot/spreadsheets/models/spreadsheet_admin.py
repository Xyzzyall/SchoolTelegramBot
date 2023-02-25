from dataclasses import dataclass, field


@dataclass
class SpreadsheetAdmin:
    unique_id: str
    fullname: str

    telegram_login: str

    secret_code: str

    roles: list[str] = field(default_factory=list)

    to_delete: bool = False
