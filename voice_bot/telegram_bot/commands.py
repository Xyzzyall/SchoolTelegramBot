from dataclasses import dataclass, field

from voice_bot.telegram_bot.base_claim import BaseClaim
from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.claims.admin_user import AdminUser
from voice_bot.telegram_bot.handlers.cmd_broadcast import CmdBroadcast
from voice_bot.telegram_bot.navigation.base_classes import NavigationTree
from voice_bot.telegram_bot.navigation.nav_tree import START_TREE, SETTINGS_TREE, SCHEDULE_TREE
from voice_bot.telegram_bot.handlers.navigation_command_handler import NavigationCommandHandler


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
    "broadcast": CommandDefinition(
        handler=CmdBroadcast,
        claims=[AdminUser]
    )
}
