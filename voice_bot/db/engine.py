import subprocess

from injector import singleton, inject
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from voice_bot.voice_bot_configurator import VoiceBotConfigurator


@singleton
class Engine:
    @inject
    def __init__(self, config: VoiceBotConfigurator):
        self._conn_srt = config.db_connection_str
        self.engine = create_async_engine(config.db_connection_str)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    def perform_migrations(self):
        alembic_args = [
            'alembic',
            '-x', f'db_url={self._conn_srt}',
            '--raiseerr',
            'upgrade', 'head',
        ]
        subprocess.run(args=alembic_args)


