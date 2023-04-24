from datetime import timedelta

from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import subqueryload

from voice_bot.db.models import User
from voice_bot.db.shortcuts import is_active
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.claims.base import BaseClaim, ClaimDefinition
from voice_bot.domain.context import Context
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.domain.services.users_service import UsersService
from voice_bot.domain.utils.user_utils import user_has_roles
from voice_bot.misc import simple_cache
from voice_bot.misc.cached import Cached
from voice_bot.misc.simple_cache import simplecache
from voice_bot.misc.user_mock import is_mocked, mock_chat_id_to_user
from voice_bot.telegram_di_scope import telegramupdate

_CACHE_KEY = "role_claim"


@telegramupdate
class RoleClaim(BaseClaim, Cached):
    @inject
    def __init__(self, session: UpdateSession, msg_bld: MessageBuilder, context: Context):
        self._context = context
        self._msg_bld = msg_bld
        self._session = session.session

    async def check(self, tg_chat_id: str, options: ClaimDefinition) -> bool:
        roles: set[str] = options.kwargs["roles"]
        maybe_user = mock_chat_id_to_user(tg_chat_id) if is_mocked(tg_chat_id) \
            else await self._try_get_user(tg_chat_id)

        if not maybe_user or not user_has_roles(maybe_user, roles):
            return False

        self._context.authorized_user = maybe_user
        self._msg_bld.push_user(maybe_user)
        return True

    @simplecache(_CACHE_KEY, lifespan=timedelta(minutes=1))
    async def _try_get_user(self, tg_chat_id: str):
        query = select(User).options(subqueryload(User.roles)) \
            .where((User.telegram_chat_id == tg_chat_id) & is_active(User))
        return await self._session.scalar(query)

    @staticmethod
    def delete_cache():
        simple_cache.delete_key(_CACHE_KEY)
