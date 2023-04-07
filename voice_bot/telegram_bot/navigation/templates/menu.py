from voice_bot.domain.claims.shortcuts import CLAIM_NOT_AUTH, CLAIM_STUDENT, CLAIM_SYSADMIN
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.templates import _wrap
from voice_bot.telegram_bot.navigation.templates.help import HELP
from voice_bot.telegram_bot.navigation.templates.schedule import STUDENT_SCHEDULE, ADMIN_SCHEDULE
from voice_bot.telegram_bot.navigation.templates.settings import SETTINGS
from voice_bot.telegram_bot.navigation.views.text_view import TextView

UNKNOWN_USER_MENU = _TreeEntry(
    element_type=TextView,
    context_vars={"is_root": "y"},
    text_template="Приветствие",
    claims=[CLAIM_NOT_AUTH],
    children={
        "how_to_auth": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title="Как авторизоваться?",
            text_template="Приветствие.Как_авторизоваться"
        )
    }
)

STUDENT_MENU = _TreeEntry(
    element_type=TextView,
    context_vars={"is_root": "y"},
    text_template="Меню",
    claims=[CLAIM_STUDENT],
    children={
        "schedule": _wrap(STUDENT_SCHEDULE, "Расписание", (0, 0)),
        "help": _wrap(HELP, position=(10, 0))
    }
)

ADMIN_MENU = _TreeEntry(
    element_type=TextView,
    context_vars={"is_root": "y"},
    text_template="Меню",
    claims=[CLAIM_SYSADMIN],
    children={
        "schedule": _wrap(ADMIN_SCHEDULE, "Расписание", (0, 0)),
        "settings": _wrap(SETTINGS, "Настройки", (10, 0)),
        "help": _wrap(HELP, position=(20, 0))
    }
)
