from injector import Injector

from voice_bot.telegram_bot.voice_bot_runner import VoiceBotRunner

if __name__ == '__main__':
    injector = Injector()
    injector.get(VoiceBotRunner).start_bot()
