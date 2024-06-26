from injector import inject

from voice_bot.domain.services.cache_service import CacheService
from voice_bot.telegram_bot.navigation.base_classes import BaseAction
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class ClearCache(BaseAction):
    @inject
    def __init__(self, cache_service: CacheService):
        super().__init__()
        self._cache_service = cache_service

    async def handle_action(self):
        match self.entry.context_vars["cache_type"]:
            case "all": self._cache_service.clear_all_cache()
            case "settings": self._cache_service.clear_settings_cache()
            case "users": self._cache_service.clear_users_cache()
        await self.tg_context.popup("Кэш успешно очищен!")

    async def get_title(self) -> str:
        raise RuntimeError("ClearCache is not supposed to generate its own title")

    