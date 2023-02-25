from voice_bot.db.models import User
from voice_bot.telegram_di_scope import telegramupdate

_USERS_STATE: dict[int, str] = {}


@telegramupdate
class Context:
    authorized_user: User = None

    def get(self) -> str:
        return _USERS_STATE[self.authorized_user.id]

    def set(self, key: str):
        _USERS_STATE[self.authorized_user.id] = key
