import functools
import uuid
from contextvars import ContextVar
from typing import Type, TypeVar

from injector import Scope, ScopeDecorator, Provider, Injector, InstanceProvider, singleton, inject

_request_id_ctx: ContextVar[uuid.UUID] = ContextVar("request_id")


class _TelegramUpdate(Scope):
    cache: dict[uuid.UUID, dict[Type, any]]

    def __init__(self, injector: Injector) -> None:
        super().__init__(injector)
        self.cache = {}

    T = TypeVar('T')

    def get(self, key: Type[T], provider: Provider[T]) -> Provider[T]:
        try:
            request_id = _request_id_ctx.get()
        except LookupError as exc:
            raise RuntimeError(
                "Request ID missing in cache."
            ) from exc
        if key in self.cache[request_id]:
            dependency = self.cache[request_id][key]
        else:
            dependency = provider.get(self.injector)
            self.cache[request_id][key] = dependency
        return InstanceProvider(dependency)

    def add_key(self, key: uuid.UUID) -> None:
        """Add a new request key to the cache."""
        self.cache[key] = {}

    def clear_key(self, key: uuid.UUID) -> None:
        """Clear the cache for a given request key."""
        del self.cache[key]


@singleton
class TelegramUpdateScopeDecorator:
    T = TypeVar('T', bound=callable)

    @inject
    def __init__(self, injector: Injector):
        self.request_scope_instance = injector.get(_TelegramUpdate)

    def __call__(self, func: T) -> T:
        @functools.wraps(func)
        async def wrapper(*args1, **kwargs1):
            rid = uuid.uuid4()
            rid_ctx = _request_id_ctx.set(rid)
            self.request_scope_instance.add_key(rid)
            try:
                await func(*args1, **kwargs1)
            finally:
                self.request_scope_instance.clear_key(rid)
                _request_id_ctx.reset(rid_ctx)

        return wrapper


telegramupdate = ScopeDecorator(_TelegramUpdate)
