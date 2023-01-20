from injector import Injector

from voice_bot.telegram_bot.voice_bot import VoiceBot

if __name__ == '__main__':
    injector = Injector()
    injector.get(VoiceBot).start_bot()
