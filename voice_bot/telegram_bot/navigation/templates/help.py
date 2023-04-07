from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry
from voice_bot.telegram_bot.navigation.views.text_view import TextView

HELP = _TreeEntry(
    element_type=TextView,
    text_template="Помощь",
    title="Помогите!"
)
