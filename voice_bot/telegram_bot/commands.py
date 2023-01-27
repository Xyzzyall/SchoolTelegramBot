from dataclasses import dataclass, field

from voice_bot.telegram_bot.base_claim import BaseClaim
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.claims.admin_user import AdminUser
from voice_bot.telegram_bot.claims.authorized_user import AuthorizedUser
from voice_bot.telegram_bot.handlers.cmd_admin_get_schedule import CmdAdminGetSchedule
from voice_bot.telegram_bot.handlers.cmd_auth_handler import CmdAuthHandler
from voice_bot.telegram_bot.handlers.cmd_start_handler import CmdStartHandler
from voice_bot.telegram_bot.handlers.cmd_student_get_schedule import CmdStudentGetSchedule


@dataclass
class CommandDefinition:
    handler: type[BaseUpdateHandler]
    claims: list[type[BaseClaim]] = field(default_factory=list)


_COMMANDS: dict[str, CommandDefinition] = {
    "start": CommandDefinition(CmdStartHandler),
    "auth": CommandDefinition(CmdAuthHandler),
    "student_schedule": CommandDefinition(
        CmdStudentGetSchedule,
        claims=[AuthorizedUser]
    ),
    "admin_schedule": CommandDefinition(
        CmdAdminGetSchedule,
        claims=[AdminUser]
    )
}
