from injector import Scope, ScopeDecorator
from telegram.ext import ContextTypes


class _TelegramUpdate(Scope):
    def get(self, key, provider):
        return provider


telegramupdate = ScopeDecorator(_TelegramUpdate)

