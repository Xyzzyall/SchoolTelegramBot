from dataclasses import dataclass, field

from voice_bot.telegram_bot.base_claim import BaseClaim
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.claims.admin_user import AdminUser
from voice_bot.telegram_bot.claims.authorized_user import AuthorizedUser
from voice_bot.telegram_bot.handlers.cmd_admin_get_schedule import CmdAdminGetSchedule
from voice_bot.telegram_bot.handlers.cmd_student_get_schedule import CmdStudentGetSchedule
from voice_bot.telegram_bot.navigation.base_classes import NavigationTree
from voice_bot.telegram_bot.navigation.nav_tree import START_TREE, SETTINGS_TREE, SCHEDULE_TREE
from voice_bot.telegram_bot.navigation.navigation_command_handler import NavigationCommandHandler


@dataclass
class CommandDefinition:
    handler: type[BaseUpdateHandler]
    claims: list[type[BaseClaim]] = field(default_factory=list)


@dataclass
class CommandWithMenuDefinition(CommandDefinition):
    handler: type[NavigationCommandHandler] = NavigationCommandHandler
    navigation: NavigationTree = field(default_factory=list)


COMMANDS: dict[str, CommandDefinition] = {
    "start": CommandWithMenuDefinition(
        navigation=START_TREE
    ),
    "settings": CommandWithMenuDefinition(
        navigation=SETTINGS_TREE
    ),
    "schedule": CommandWithMenuDefinition(
        navigation=SCHEDULE_TREE
    ),
    "student_schedule": CommandDefinition(
        CmdStudentGetSchedule,
        claims=[AuthorizedUser]
    ),
    "admin_schedule": CommandDefinition(
        CmdAdminGetSchedule,
        claims=[AdminUser]
    )
}
