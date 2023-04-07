import copy

from voice_bot.telegram_bot.navigation.base_classes import _TreeEntry


def _wrap(entry: _TreeEntry, title: str = None, position: tuple[int, int] = None):
    copied = copy.copy(entry)
    if title:
        copied.title = title
    if position:
        copied.position = position
    if "is_root" in copied.context_vars:
        copied.context_vars.pop("is_root")
    return copied
