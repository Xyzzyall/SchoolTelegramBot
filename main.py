import os
import time

from injector import Injector

from voice_bot.db.engine import Engine
from voice_bot.telegram_bot.voice_bot_runner import VoiceBotRunner

if __name__ == '__main__':
    injector = Injector()
    injector.get(Engine).perform_migrations()
    injector.get(VoiceBotRunner).start_bot()
