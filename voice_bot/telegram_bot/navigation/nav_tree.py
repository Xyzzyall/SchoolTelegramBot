from voice_bot.telegram_bot.navigation.base_classes import NavigationTree
from voice_bot.telegram_bot.navigation.templates.menu import UNKNOWN_USER_MENU, STUDENT_MENU, ADMIN_MENU
from voice_bot.telegram_bot.navigation.templates.reminder import STUDENT_LESSON_REMINDER

START_MENU_TREE: NavigationTree = [
    UNKNOWN_USER_MENU,
    STUDENT_MENU,
    ADMIN_MENU
]

REMINDER_TREE: NavigationTree = [
    STUDENT_LESSON_REMINDER
]
