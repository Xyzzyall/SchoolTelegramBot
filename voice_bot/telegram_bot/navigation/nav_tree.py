from voice_bot.telegram_bot.claims.admin_user import AdminUser
from voice_bot.telegram_bot.claims.authorized_user import AuthorizedUser
from voice_bot.telegram_bot.navigation.actions.clear_cache import ClearCache
from voice_bot.telegram_bot.navigation.actions.create_schedule_tables import CreateScheduleTables
from voice_bot.telegram_bot.navigation.actions.set_reminder import SetReminder
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry, NavigationTree
from voice_bot.telegram_bot.navigation.views.greeting import Greeting
from voice_bot.telegram_bot.navigation.views.next_lesson import NextLesson
from voice_bot.telegram_bot.navigation.views.schedule import Schedule
from voice_bot.telegram_bot.navigation.views.settings import Settings
from voice_bot.telegram_bot.navigation.views.standard_schedule import StandardSchedule
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_bot.navigation.views.timebounded_schedule import TimeBoundedSchedule


START_TREE: NavigationTree = [_TreeEntry(
    element_type=Greeting,
    children={
        "how_to_auth": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title_override="Как авторизоваться?",
            inner_text_template_override="Приветствие.Как_авторизоваться"
        )
    }
)]

SCHEDULE_TREE: NavigationTree = [
    _TreeEntry(
        element_type=Schedule,
        inner_text_template_override="Расписание",
        claims=[AuthorizedUser],
        children={
            "look_schedule": _TreeEntry(
                element_type=TextView,
                position=(10, 0),
                title_override="Узнать расписание",
                inner_text_template_override="Расписание.Узнать",
                children={
                    "next_lesson": _TreeEntry(
                        element_type=NextLesson,
                        position=(10, 0),
                        title_override="Следующее занятие"
                    ),
                    "standard_schedule": _TreeEntry(
                        element_type=StandardSchedule,
                        position=(20, 0),
                        title_override="Стандартное расписание"
                    ),
                    "next_seven_days": _TreeEntry(
                        element_type=TimeBoundedSchedule,
                        position=(30, 0),
                        title_override="Следующие 7 дней",
                        context_vars={
                            "time_bound": "7"
                        }
                    )
                }
            ),
            "reminders": _TreeEntry(
                element_type=TextView,
                position=(20, 0),
                title_override="Напоминания",
                inner_text_template_override="Расписание.Напоминая",
                children={
                    "24hours": _TreeEntry(
                        element_type=SetReminder,
                        position=(10, 0),
                        context_vars={
                            "title": "За сутки",
                            "reminder": "за сутки"
                        }
                    ),
                    "1hour": _TreeEntry(
                        element_type=SetReminder,
                        position=(20, 0),
                        context_vars={
                            "title": "За час",
                            "reminder": "за час"
                        }
                    )
                }
            )
        }
    ),
    _TreeEntry(
        element_type=Schedule,
        inner_text_template_override="РасписаниеАдмин",
        claims=[AdminUser],
        children={
            "look_schedule": _TreeEntry(
                element_type=TextView,
                title_override="Узнать расписание",
                inner_text_template_override="Расписание.Узнать",
                position=(10, 0),
                children={
                    "next_lesson": _TreeEntry(
                        element_type=NextLesson,
                        position=(10, 0),
                        title_override="Следующее занятие",
                        context_vars={
                            "is_admin": "y"
                        }
                    ),
                    "today": _TreeEntry(
                        element_type=TimeBoundedSchedule,
                        position=(20, 0),
                        title_override="На сегодня",
                        context_vars={
                            "time_bound": "today",
                            "is_admin": "y"
                        }
                    ),
                    "tomorrow": _TreeEntry(
                        element_type=TimeBoundedSchedule,
                        position=(30, 0),
                        title_override="На завтра",
                        context_vars={
                            "time_bound": "tomorrow",
                            "is_admin": "y"
                        }
                    )
                }
            ),
            "reminders": _TreeEntry(
                element_type=TextView,
                title_override="Напоминания",
                inner_text_template_override="Расписание.Напоминая",
                position=(20, 0),
                children={
                    "1hour": _TreeEntry(
                        element_type=SetReminder,
                        position=(10, 0),
                        context_vars={
                            "title": "За час",
                            "reminder": "за час",
                            "is_admin": "y"
                        }
                    ),
                    "30minutes": _TreeEntry(
                        element_type=SetReminder,
                        position=(20, 0),
                        context_vars={
                            "title": "За полчаса",
                            "reminder": "за 30 минут",
                            "is_admin": "y"
                        }
                    )
                }
            )
        }
    )
]

SETTINGS_TREE: NavigationTree = [_TreeEntry(
    element_type=Settings,
    children={
        "clear_cache": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title_override="Очистить кэш",
            inner_text_template_override="Настройки.Очистка_кэша",
            claims=[AdminUser],
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
            claims=[AdminUser],
            children={
                "create_tables": _TreeEntry(
                    element_type=CreateScheduleTables,
                    position=(10, 0),
                    title_override="Создать таблицы с расписанием",
                )
            }
        )
    }
)]
