from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class BaseClaim(ABC):
    @abstractmethod
    async def check(self, tg_login: str, options: "ClaimDefinition") -> bool:
        pass


@dataclass
class ClaimDefinition:
    base_class: type[BaseClaim]
    kwargs: dict[str, any] = field(default_factory=dict)
