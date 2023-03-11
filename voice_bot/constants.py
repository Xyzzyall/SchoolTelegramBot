from datetime import timedelta

REMINDERS_OPTIONS = {
    "за сутки": timedelta(hours=27),  # для возможности отмены
    "за час": timedelta(hours=1),
    "за 15 минут": timedelta(minutes=15),
    "за 30 минут": timedelta(minutes=30)
}

REMINDERS_TEXT = {
    timedelta(hours=27): "завтра",
    timedelta(hours=24): "завтра",
    timedelta(hours=1): "через час",
    timedelta(minutes=15): "через 15 минут",
    timedelta(minutes=30): "через полчаса"
}

REMINDER_THRESHOLD = timedelta(minutes=5)

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
