from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from telegram import Update
from telegram.ext import ContextTypes

from voice_bot.telegram_bot.base_claim import BaseClaim


@dataclass
class NavigationContext:
    root_cmd: str
    tree_path: list[str]
    context_vars: dict[str, str]
    kwargs: dict[str, str]


class BaseNavigation(ABC):
    nav_context: NavigationContext
    update: Update
    context: ContextTypes.DEFAULT_TYPE

    def push_context(self, nav_context: NavigationContext, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.nav_context = nav_context
        self.update = update
        self.context = context

    @abstractmethod
    async def get_title(self) -> str:
        pass

    @abstractmethod
    async def handle(self) -> NavigationContext | None:
        pass


class BaseAction(BaseNavigation, ABC):
    pass

@dataclass
class _TreeEntry:
    element_type: type[BaseNavigation]
    position: (int, int) = (0, 0)
    claims: list[type[BaseClaim]] = field(default_factory=list)
    children: dict[str, "_TreeEntry"] = field(default_factory=dict)
    title_override: str | None = None
    inner_text_template_override: str | None = None
    kwargs: dict[str, str] = field(default_factory=dict)


NavigationTree = list[_TreeEntry]


@dataclass
class _ButtonStab:
    position: (int, int)
    title: str
    kwargs: dict[str, str] = field(default_factory=dict)


class BaseView(BaseNavigation, ABC):
    @abstractmethod
    async def get_message_text(self) -> str:
        pass

    @abstractmethod
    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        pass


class BaseRootView(BaseView, ABC):
    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        return {}

    async def handle(self) -> NavigationContext | None:
        return self.nav_context

    async def get_title(self) -> str:
        raise RuntimeError("Root view has no title")
