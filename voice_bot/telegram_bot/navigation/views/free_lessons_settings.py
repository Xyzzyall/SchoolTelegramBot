from injector import inject

from voice_bot.constants import DAYS_OF_THE_WEEK
from voice_bot.domain.services.book_lesson_service import BookLessonsService
from voice_bot.telegram_bot.navigation.base_classes import BaseView, NavigationContext, _ButtonStab
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class FreeLessonsSettingsView(BaseView):
    DAY = "day"

    @inject
    def __init__(self, book: BookLessonsService):
        super().__init__()
        self.book = book

    async def get_message_text(self) -> str:
        if self.get_view_kwarg("_state", False) == self.DAY:
            weekday = self.get_view_kwarg("_weekday", False)
            return f"{DAYS_OF_THE_WEEK[weekday+1].capitalize()}, отметь окна, которые будут доступны для бронирования"
        return "Выбери день недели"

    async def get_view_buttons(self) -> dict[str, _ButtonStab]:
        res = {"_back": _ButtonStab((1000, 0), "Назад", {"_action": "back"})}
        if self.get_view_kwarg("_state", False) == self.DAY:
            weekday = self.get_view_kwarg("_weekday", False)
            lessons = await self.book.get_free_lessons_weekday(weekday)
            for i in range(9, 22):
                key = f"{i:02d}:00"
                time_end = f"{i:02d}:50"
                res[f"_free{i}"] = _ButtonStab(
                    (100+i, 0),
                    f"{'✅' if key in lessons else '❌'} окно c {key} по {time_end}",
                    {"_action": "toggle", "_time_start": key, "_time_end": time_end}
                )
        else:
            for i in range(7):
                res[f"_day{i}"] = _ButtonStab(
                    (100+i, 0),
                    DAYS_OF_THE_WEEK[i + 1].capitalize(),
                    {"_state": self.DAY, "_weekday": i}
                )
        return res

    async def get_title(self) -> str:
        raise RuntimeError("not implemented")

    async def handle(self) -> NavigationContext | None:
        match self.get_view_kwarg("_action"):
            case "toggle":
                weekday = self.get_view_kwarg("_weekday", False)
                time_start = self.get_view_kwarg("_time_start")
                time_end = self.get_view_kwarg("_time_end")
                await self.book.toggle_free_lesson(weekday, time_start, time_end)
            case "back":
                match self.get_view_kwarg("_state", False):
                    case self.DAY:
                        self.set_view_kwarg("_state", None)
                        self.get_view_kwarg("_weekday")
                    case _:
                        self.erase_view_kwargs()
                        self.nav_context.tree_path.pop()
        return self.nav_context
