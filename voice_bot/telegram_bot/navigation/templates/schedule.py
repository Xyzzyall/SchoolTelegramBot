from voice_bot.domain.claims.shortcuts import CLAIM_STUDENT, CLAIM_SCHEDULE
from voice_bot.telegram_bot.navigation.actions.set_reminder import SetReminder
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.book_lesson import StudentBookLesson, AdminBookLesson
from voice_bot.telegram_bot.navigation.views.cancel_day import CancelDayView
from voice_bot.telegram_bot.navigation.views.cancel_lesson import StudentCancelLessonView, AdminCancelLessonView
from voice_bot.telegram_bot.navigation.views.lesson_swap import LessonSwapView
from voice_bot.telegram_bot.navigation.views.next_lesson import NextLesson
from voice_bot.telegram_bot.navigation.views.standard_schedule import StandardSchedule
from voice_bot.telegram_bot.navigation.views.text_view import TextView
from voice_bot.telegram_bot.navigation.views.timebounded_schedule import TimeBoundedSchedule


STUDENT_SCHEDULE = _TreeEntry(
    element_type=TextView,
    text_template="Расписание",
    context_vars={"is_root": "y"},
    claims=[CLAIM_STUDENT],
    children={
        "look_schedule": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title="Узнать расписание",
            text_template="Расписание.Узнать",
            children={
                "standard_schedule": _TreeEntry(
                    element_type=StandardSchedule,
                    position=(10, 0),
                    title="Обычное расписание"
                ),
                "next_lesson": _TreeEntry(
                    element_type=NextLesson,
                    position=(20, 0),
                    title="Следующее занятие"
                ),
                "next_seven_days": _TreeEntry(
                    element_type=TimeBoundedSchedule,
                    position=(30, 0),
                    title="Следующие 7 дней",
                    context_vars={
                        "time_bound": "7"
                    }
                )
            }
        ),
        "reminders": _TreeEntry(
            element_type=TextView,
            position=(20, 0),
            title="Напоминания",
            text_template="Расписание.Напоминая",
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
        ),
        "cancel_lesson": _TreeEntry(
            element_type=StudentCancelLessonView,
            title="Отмена занятий",
            position=(30, 0)
        ),
        "book_lesson": _TreeEntry(
            element_type=StudentBookLesson,
            title="Записаться на занятие",
            position=(40, 0)
        )
    }
)


ADMIN_SCHEDULE = _TreeEntry(
    element_type=TextView,
    text_template="РасписаниеАдмин",
    context_vars={"is_root": "y"},
    claims=[CLAIM_SCHEDULE],
    children={
        "look_schedule": _TreeEntry(
            element_type=TextView,
            title="Узнать расписание",
            text_template="Расписание.Узнать",
            position=(10, 0),
            children={
                "next_lesson": _TreeEntry(
                    element_type=NextLesson,
                    position=(10, 0),
                    title="Следующее занятие",
                    context_vars={
                        "is_admin": "y"
                    }
                ),
                "today": _TreeEntry(
                    element_type=TimeBoundedSchedule,
                    position=(20, 0),
                    title="На сегодня",
                    context_vars={
                        "time_bound": "today",
                        "is_admin": "y"
                    }
                ),
                "tomorrow": _TreeEntry(
                    element_type=TimeBoundedSchedule,
                    position=(30, 0),
                    title="На завтра",
                    context_vars={
                        "time_bound": "tomorrow",
                        "is_admin": "y"
                    }
                ),
                "week": _TreeEntry(
                    element_type=TimeBoundedSchedule,
                    position=(40, 0),
                    title="Следующие 7 дней",
                    context_vars={
                        "time_bound": "7",
                        "is_admin": "y"
                    }
                )
            }
        ),
        "reminders": _TreeEntry(
            element_type=TextView,
            title="Напоминания",
            text_template="Расписание.Напоминая",
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
        ),
        "cancel_lesson_menu": _TreeEntry(
            element_type=TextView,
            text_template="Отмена занятий",
            title="Отмена занятий",
            position=(30, 0),
            children={
                "cancel_lesson": _TreeEntry(
                    element_type=AdminCancelLessonView,
                    title="Отмена конкретного занятия",
                    position=(10, 0),
                ),
                "cancel_on_day": _TreeEntry(
                    element_type=CancelDayView,
                    title="Отменить все занятия в день",
                    position=(20, 0),
                )
            }
        ),
        "book_lesson": _TreeEntry(
            element_type=AdminBookLesson,
            title="Записать ученика на занятие",
            position=(40, 0)
        ),
        "swap_lessons": _TreeEntry(
            element_type=LessonSwapView,
            title="Перемещение уроков",
            position=(50, 0)
        )
    }
)
