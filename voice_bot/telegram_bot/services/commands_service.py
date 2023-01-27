from injector import singleton, inject, Injector
from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.telegram_di_scope import _TelegramUpdate
from voice_bot.telegram_bot.commands import _COMMANDS


@singleton
class CommandsService:
    @inject
    def __init__(self, injector: Injector):
        self._injector = injector

    async def check_claims_for_command(self, cmd_name: str,
                                       update: Update,
                                       context: ContextTypes.DEFAULT_TYPE) -> bool:
        if cmd_name not in _COMMANDS:
            raise KeyError(f"Command {cmd_name} is not found")

        cmd_def = _COMMANDS[cmd_name]

        for claim in cmd_def.claims:
            if not await self._injector.get(claim, _TelegramUpdate).handle(update, context):
                return False
        return True
