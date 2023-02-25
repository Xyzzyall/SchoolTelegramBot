from voice_bot.domain.claims.shortcuts import CLAIM_SYSADMIN
from voice_bot.telegram_bot.navigation.actions.clear_cache import ClearCache
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry, NavigationTree
from voice_bot.telegram_bot.navigation.templates.greet import UNKNOWN_USER_GREET, STUDENT_GREET, ADMIN_GREET
from voice_bot.telegram_bot.navigation.templates.schedule import STUDENT_SCHEDULE, ADMIN_SCHEDULE
from voice_bot.telegram_bot.navigation.views.settings import Settings
from voice_bot.telegram_bot.navigation.views.text_view import TextView

START_TREE: NavigationTree = [
    UNKNOWN_USER_GREET,
    STUDENT_GREET,
    ADMIN_GREET
]

SCHEDULE_TREE: NavigationTree = [
    STUDENT_SCHEDULE,
    ADMIN_SCHEDULE
]

SETTINGS_TREE: NavigationTree = [_TreeEntry(
    element_type=Settings,
    children={
        "clear_cache": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title_override="Очистить кэш",
            inner_text_template_override="Настройки.Очистка_кэша",
            claims=[CLAIM_SYSADMIN],
            children={
                "all_cache": _TreeEntry(
                    element_type=ClearCache,
                    position=(10, 0),
                    title_override="Очистить весь кэш (может вызвать лёгкие тормоза!)",
                    context_vars={
                        "cache_type": "all"
                    }
                ),
                "settings_cache": _TreeEntry(
                    element_type=ClearCache,
                    position=(20, 0),
                    title_override="Кэш настроек",
                    context_vars={
                        "cache_type": "settings"
                    }
                ),
                "users_cache": _TreeEntry(
                    element_type=ClearCache,
                    position=(30, 0),
                    title_override="Кэш учеников",
                    context_vars={
                        "cache_type": "users"
                    }
                ),
            }
        ),
        "schedule": _TreeEntry(
            element_type=TextView,
            position=(20, 0),
            title_override="Расписание",
            inner_text_template_override="Настройки.Расписание",
            claims=[CLAIM_SYSADMIN],
            children={
            }
        )
    }
)]
