from voice_bot.domain.claims.shortcuts import CLAIM_SYSADMIN
from voice_bot.telegram_bot.navigation.actions.clear_cache import ClearCache
from voice_bot.telegram_bot.navigation.actions.perform_sync import PerformSync
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.text_view import TextView

SETTINGS = _TreeEntry(
    element_type=TextView,
    context_vars={"is_root": "y"},
    text_template="Настройки",
    children={
        "clear_cache": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title="Очистить кэш",
            text_template="Настройки.Очистка_кэша",
            claims=[CLAIM_SYSADMIN],
            children={
                "settings_cache": _TreeEntry(
                    element_type=ClearCache,
                    position=(20, 0),
                    title="Кэш настроек",
                    context_vars={
                        "cache_type": "settings"
                    }
                ),
            }
        ),
        "synchronization": _TreeEntry(
            element_type=TextView,
            position=(20, 0),
            title="Синхронизация",
            text_template="Настройки.Синхронизация",
            claims=[CLAIM_SYSADMIN],
            children={
                "perform_sync": _TreeEntry(
                    element_type=PerformSync,
                    position=(20, 0),
                    title="Провести синхронизацию",
                ),
            }
        )
    }
)
