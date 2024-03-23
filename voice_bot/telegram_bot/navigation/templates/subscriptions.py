from voice_bot.domain.claims.shortcuts import CLAIM_STUDENT, CLAIM_SYSADMIN
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.action_logs import ActionLogsView
from voice_bot.telegram_bot.navigation.views.actions_editor import ActionsEditorView
from voice_bot.telegram_bot.navigation.views.empty_subs import EmptySubsView
from voice_bot.telegram_bot.navigation.views.student_subscriptions import StudentSubscriptions
from voice_bot.telegram_bot.navigation.views.text_view import TextView

ACTION_LOGS = _TreeEntry(
    element_type=TextView,
    claims=[CLAIM_SYSADMIN],
    text_template="Просмотр прошедших занятий и абонементы",
    children={
        "subs": _TreeEntry(
            element_type=ActionLogsView,
            position=(0, 0),
            title="Абонементы"
        ),
        "actions_editor": _TreeEntry(
            element_type=ActionsEditorView,
            position=(1, 0),
            title="Прошедшие уроки"
        ),
        "empty_subs": _TreeEntry(
            element_type=EmptySubsView,
            position=(2, 0),
            title="Просроченные ученики"
        )
    }
)


STUDENT_SUBS = _TreeEntry(
    element_type=StudentSubscriptions,
    claims=[CLAIM_STUDENT]
)
