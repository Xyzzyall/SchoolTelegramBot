from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.lesson_reminder import StudentLessonReminderView

STUDENT_LESSON_REMINDER = _TreeEntry(
    element_type=StudentLessonReminderView
)
