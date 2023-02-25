from voice_bot.domain.claims.shortcuts import CLAIM_NOT_AUTH, CLAIM_STUDENT, CLAIM_SYSADMIN
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.text_view import TextView

UNKNOWN_USER_GREET = _TreeEntry(
    element_type=TextView,
    inner_text_template_override="Приветствие",
    context_vars={"is_root": "y"},
    claims=[CLAIM_NOT_AUTH],
    children={
        "how_to_auth": _TreeEntry(
            element_type=TextView,
            position=(10, 0),
            title_override="Как авторизоваться?",
            inner_text_template_override="Приветствие.Как_авторизоваться"
        )
    }
)

STUDENT_GREET = _TreeEntry(
    element_type=TextView,
    inner_text_template_override="Приветствие",
    context_vars={"is_root": "y"},
    claims=[CLAIM_STUDENT],
    children={
    }
)

ADMIN_GREET = _TreeEntry(
    element_type=TextView,
    inner_text_template_override="Приветствие",
    context_vars={"is_root": "y"},
    claims=[CLAIM_SYSADMIN],
    children={
    }
)
