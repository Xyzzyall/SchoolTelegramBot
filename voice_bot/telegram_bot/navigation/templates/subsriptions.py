from voice_bot.domain.claims.shortcuts import CLAIM_SYSADMIN, CLAIM_STUDENT
from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.action_logs import ActionLogsView
from voice_bot.telegram_bot.navigation.views.student_subscriptions import StudentSubscriptions

ACTION_LOGS = _TreeEntry(
    element_type=ActionLogsView,
)

STUDENT_SUBS = _TreeEntry(
    element_type=StudentSubscriptions,
    claims=[CLAIM_STUDENT]
)
