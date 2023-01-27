from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import ContextTypes


class BaseClaim(ABC):
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        handled = await self.handle(update, context)
        if not handled:
            await self.on_fail(update, context)
        return handled

    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        pass

    @abstractmethod
    async def on_fail(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass
