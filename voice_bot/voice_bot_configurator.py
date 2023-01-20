import os

from injector import singleton


@singleton
class VoiceBotConfigurator:
    def __init__(self):
        self.telegram_bot_token = os.environ.get("VOICE_BOT_TELEGRAM_TOKEN")

