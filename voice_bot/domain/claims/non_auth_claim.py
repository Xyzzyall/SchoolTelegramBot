from injector import inject
from sqlalchemy import select

from voice_bot.db.models import User
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.claims.base import BaseClaim, ClaimDefinition
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class NonAuthClaim(BaseClaim):
    @inject
    def __init__(self, session: UpdateSession):
        self._session = session()

    async def check(self, tg_chat_id: str, options: ClaimDefinition) -> bool:
        query = select(User.telegram_login).where(User.telegram_chat_id == tg_chat_id)
        return not (await self._session.scalar(query))

