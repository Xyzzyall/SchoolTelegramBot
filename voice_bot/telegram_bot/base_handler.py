from abc import abstractmethod, ABC

from telegram import Update
from telegram.ext import ContextTypes


class BaseUpdateHandler(ABC):
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass


class BaseScheduleHandler(ABC):
    @abstractmethod
    async def handle(self, context: ContextTypes.DEFAULT_TYPE):
        pass
