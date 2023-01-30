from voice_bot.telegram_bot.navigation.base_classes import BaseView
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class Schedule(BaseView):
    pass


@telegramupdate
class ObserveSchedule(BaseView):
    pass


@telegramupdate
class ScheduleReminders(BaseView):
    pass
