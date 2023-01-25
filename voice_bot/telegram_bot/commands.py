from dataclasses import dataclass

from voice_bot.telegram_bot.base_handler import BaseUpdateHandler
from voice_bot.telegram_bot.handlers.cmd_auth_handler import CmdAuthHandler
from voice_bot.telegram_bot.handlers.cmd_start_handler import CmdStartHandler


@dataclass
class CommandDefinition:
    command_nade: str
    handler: type[BaseUpdateHandler]


_COMMANDS: list[CommandDefinition] = [
    CommandDefinition("start", CmdStartHandler),
    CommandDefinition("auth", CmdAuthHandler)
]
