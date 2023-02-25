from voice_bot.domain.claims.shortcuts import CLAIM_STUDENT, CLAIM_SCHEDULE
from voice_bot.telegram_bot.navigation.actions.set_reminder import SetReminder
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.next_lesson import NextLesson
from voice_bot.telegram_bot.navigation.views.standard_schedule import StandardSchedule
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_bot.navigation.views.timebounded_schedule import TimeBoundedSchedule


STUDENT_SCHEDULE = _TreeEntry(
    element_type=TextView,
    inner_text_template_override="Расписание",
    context_vars={"is_root": "y"},
    claims=[CLAIM_STUDENT],
    children={
        "look_schedule": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title_override="Узнать расписание",
            inner_text_template_override="Расписание.Узнать",
            children={
                "standard_schedule": _TreeEntry(
                    element_type=StandardSchedule,
                    position=(10, 0),
                    title_override="Обычное расписание"
                ),
                "next_lesson": _TreeEntry(
                    element_type=NextLesson,
                    position=(20, 0),
                    title_override="Следующее занятие"
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
)


ADMIN_SCHEDULE = _TreeEntry(
    element_type=TextView,
    inner_text_template_override="РасписаниеАдмин",
    context_vars={"is_root": "y"},
    claims=[CLAIM_SCHEDULE],
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
                ),
                "week": _TreeEntry(
                    element_type=TimeBoundedSchedule,
                    position=(40, 0),
                    title_override="Следующие 7 дней",
                    context_vars={
                        "time_bound": "7",
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
                    }
                ),
                "30minutes": _TreeEntry(
                    element_type=SetReminder,
                    position=(20, 0),
                    context_vars={
                        "title": "За полчаса",
                        "reminder": "за 30 минут",
                    }
                ),
                "15minutes": _TreeEntry(
                    element_type=SetReminder,
                    position=(20, 1),
                    context_vars={
                        "title": "За 15 минут",
                        "reminder": "за 15 минут"
                    }
                )
            }
        )
    }
)
