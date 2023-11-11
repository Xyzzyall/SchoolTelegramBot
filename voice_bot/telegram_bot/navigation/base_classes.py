import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from telegram import InlineKeyboardButton

from voice_bot.domain.claims.base import ClaimDefinition


# @dataclass
# class NavigationContext:
#     root_cmd: str
#     tree_path: list[str]
#     context_vars: dict[str, str]
#     kwargs: dict[str, str]

@dataclass
class NavigationContext:
    root: "_TreeEntry"
    tree_path: list[str]
    kwargs: dict[str, any]

    def __hash__(self):
        return super.__str__(self).__hash__()


class TgContext(ABC):
    @abstractmethod
    def get_chat_id(self) -> str:
        pass

    @abstractmethod
    async def popup(self, text: str):
        pass

    @abstractmethod
    async def message(self, text: str, buttons: list[list[InlineKeyboardButton]]):
        pass


class BaseNavigation(ABC):
    def __init__(self):
        self.nav_context: NavigationContext = None
        self.tg_context: TgContext = None
        self.entry: _TreeEntry = None

    def push_context(self, nav_context: NavigationContext, tg_context: TgContext, entry: "_TreeEntry"):
        self.nav_context = nav_context
        self.tg_context = tg_context
        self.entry = entry

    @abstractmethod
    async def get_title(self) -> str:
        pass

    @abstractmethod
    async def handle(self) -> NavigationContext | None:
        pass


class BaseAction(BaseNavigation, ABC):
    @abstractmethod
    async def handle_action(self):
        pass

    async def handle(self) -> NavigationContext | None:
        await self.handle_action()
        self.nav_context.tree_path.pop()
        return self.nav_context


@dataclass
class _TreeEntry:
    element_type: type[BaseNavigation]
    position: (int, int) = (0, 0)
    claims: list[ClaimDefinition] = field(default_factory=list)
    children: dict[str, "_TreeEntry"] = field(default_factory=dict)
    title: str | None = None
    text_template: str | None = None
    context_vars: dict[str, str] = field(default_factory=dict)
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))


NavigationTree = list[_TreeEntry]


@dataclass
class _ButtonStab:
    position: (int, int)
    title: str
    kwargs: dict[str, any] = field(default_factory=dict)


class BaseView(BaseNavigation, ABC):
    @abstractmethod
    async def get_message_text(self) -> str:
        pass

    @abstractmethod
    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        pass

    def get_view_kwarg(self, key: str, pop: bool = True) -> any:
        if key not in self.nav_context.kwargs:
            return None
        return self.nav_context.kwargs.pop(key) if pop else self.nav_context.kwargs[key]

    def erase_view_kwargs(self):
        for key in [*self.nav_context.kwargs.keys()]:
            if key[0] == "_":
                self.nav_context.kwargs.pop(key)

    def set_view_kwarg(self, key: str, val: any):
        self.nav_context.kwargs[key] = val

    def close(self):
        self.erase_view_kwargs()
        self.nav_context.tree_path.pop()


class BaseRootView(BaseView, ABC):
    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        return {}

    async def handle(self) -> NavigationContext | None:
        return self.nav_context

    async def get_title(self) -> str:
        raise RuntimeError("Root view has no title")
