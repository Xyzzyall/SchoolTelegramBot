from injector import inject

from voice_bot.db.engine import Engine
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class UpdateSession:
    @inject
    def __init__(self, engine: Engine):
        self._engine = engine
        self.session = self._engine.async_session()

    def __call__(self):
        return self.session
