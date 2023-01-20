from dataclasses import dataclass

from voice_bot.telegram_bot.base_handler import BaseHandler
from voice_bot.telegram_bot.handlers.cmd_start_handler import CmdStartHandler


@dataclass
class CommandDefinition:
    command_nade: str
    handler: type[BaseHandler]


_COMMANDS: tuple[CommandDefinition] = (
    CommandDefinition("start", CmdStartHandler),
)

