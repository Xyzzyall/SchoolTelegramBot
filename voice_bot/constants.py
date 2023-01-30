from datetime import timedelta

REMINDERS_OPTIONS = {
    "за сутки": timedelta(hours=24),
    "за час": timedelta(hours=1),
    "за 15 минут": timedelta(minutes=15),
    "за 30 минут": timedelta(minutes=30)
}

DAYS_OF_THE_WEEK = [
    None,
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье"
]
