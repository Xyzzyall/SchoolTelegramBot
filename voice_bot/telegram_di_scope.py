from injector import Scope, ScopeDecorator


class _TelegramUpdate(Scope):
    def get(self, key, provider):
        return provider


telegramupdate = ScopeDecorator(_TelegramUpdate)

