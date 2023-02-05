from injector import inject

from voice_bot.services.schedule_service import ScheduleService
from voice_bot.telegram_bot.navigation.base_classes import BaseAction
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class CreateScheduleTables(BaseAction):
    @inject 
    def __init__(self, schedule: ScheduleService):
        self._schedule = schedule
    
    async def handle_action(self):
        did_something = await self._schedule.create_tables_if_not_exist()
        if did_something:
            await self.update.callback_query.answer("Отсутствующие таблицы созданы")
        else:
            await self.update.callback_query.answer("Таблицы уже созданы")

    async def get_title(self) -> str:
        raise RuntimeError("CreateScheduleTables is supposed to have title override")

    