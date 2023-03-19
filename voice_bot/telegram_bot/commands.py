from dataclasses import dataclass, field

from voice_bot.domain.claims.base import ClaimDefinition
from voice_bot.domain.claims.role_claim import RoleClaim
from voice_bot.domain.roles import UserRoles
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.handlers.cmd_broadcast import CmdBroadcast
from voice_bot.telegram_bot.handlers.cmd_xxx import CmdXxx
from voice_bot.telegram_bot.handlers.navigation_command_handler import NavigationCommandHandler
from voice_bot.telegram_bot.navigation.base_classes import NavigationTree
from voice_bot.telegram_bot.navigation.nav_tree import START_MENU_TREE


@dataclass
class CommandDefinition:
    handler: type[BaseUpdateHandler]
    claims: list[ClaimDefinition] = field(default_factory=list)


@dataclass
class CommandWithMenuDefinition(CommandDefinition):
    handler: type[NavigationCommandHandler] = NavigationCommandHandler
    navigation: NavigationTree = field(default_factory=list)


COMMANDS: dict[str, CommandDefinition] = {
    "start": CommandWithMenuDefinition(
        navigation=START_MENU_TREE
    ),
    "broadcast": CommandDefinition(
        handler=CmdBroadcast,
        claims=[ClaimDefinition(RoleClaim, {"roles": set(UserRoles.sysadmin)})]
    ),
    "xxx": CommandDefinition(
        handler=CmdXxx
    )
}
