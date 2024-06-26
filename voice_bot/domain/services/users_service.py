import structlog
from injector import inject
from sqlalchemy import select
from sqlalchemy.orm import subqueryload

from voice_bot.db.enums import YesNo
from voice_bot.db.models import UserRole, User
from voice_bot.db.shortcuts import is_active
from voice_bot.db.update_session import UpdateSession
from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.misc.user_mock import try_mock_subj_to_chat_id
from voice_bot.telegram_bot.navigation.base_classes import NavigationTree
from voice_bot.telegram_bot.navigation.navigation import Navigation
from voice_bot.telegram_bot.telegram_bot_proxy import TelegramBotProxy
from voice_bot.telegram_di_scope import telegramupdate


@telegramupdate
class UsersService:
    @inject
    def __init__(self,
                 msg_builder: MessageBuilder,
                 tg_bot_proxy: TelegramBotProxy,
                 session: UpdateSession,
                 navigation: Navigation):
        self._navigation = navigation
        self._msg_builder = msg_builder
        self._session = session.session
        self._tg_bot_proxy = tg_bot_proxy
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def send_text_message_to_roles(self, template_or_msg: str, roles: set[str], send_as_is: bool = False):
        query = select(User).where(User.roles.any(UserRole.role_name.in_(roles)))
        users = (await self._session.scalars(query)).all()

        for user in users:
            self._msg_builder.push_user(user)
            message = template_or_msg if send_as_is else await self._msg_builder.format(template_or_msg)
            await self.send_text_message(user, message)

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self._session.scalar(select(User).where(is_active(User) & (User.id == user_id))
                                          .options(subqueryload(User.roles)))

    async def get_user_by_unique_name(self, unique_name: str) -> User | None:
        return await self._session.scalar(select(User).where(is_active(User) & (User.unique_name == unique_name))
                                          .options(subqueryload(User.roles)))

    async def get_user_by_tg_id(self, chat_id: str) -> User | None:
        return await self._session.scalar(select(User).where(is_active(User) & (User.telegram_chat_id == chat_id))
                                          .options(subqueryload(User.roles)))

    async def get_all_admins(self) -> list[User]:
        query = select(User).where(is_active(User) & (User.is_admin == YesNo.YES))
        return (await self._session.scalars(query)).all()

    async def get_all_regular_users(self) -> list[User]:
        query = select(User).where(is_active(User) & (User.is_admin == YesNo.NO))
        return (await self._session.scalars(query)).all()

    async def find_user_by_fullname(self, fullname: str) -> User | None:
        query = select(User).where(is_active(User) & User.fullname.like(fullname))
        return await self._session.scalar(query)

    async def get_all_regular_users_ordered(self) -> list[User]:
        query = select(User).where(is_active(User) & (User.is_admin == YesNo.NO)).order_by(User.fullname)
        return (await self._session.scalars(query)).all()

    async def send_template(self, user: User | str, template: str, mock: bool = True):
        chat_id = user.telegram_chat_id if isinstance(user, User) else user
        if mock:
            chat_id = try_mock_subj_to_chat_id(user)
        if not chat_id:
            return
        text = await self._msg_builder.format(template)
        await self._logger.info("sent message to user", chat_id=chat_id, text=text)
        await self._tg_bot_proxy.bot.send_message(chat_id, text, parse_mode='Markdown')

    async def send_text_message(self, user: User | str, text: str, mock: bool = True):
        chat_id = user.telegram_chat_id if isinstance(user, User) else user
        if mock:
            chat_id = try_mock_subj_to_chat_id(user)
        if not chat_id:
            return
        await self._logger.info("sent message to user", chat_id=chat_id, text=text)
        await self._tg_bot_proxy.bot.send_message(chat_id, text, parse_mode='Markdown')

    async def send_text_message_to_admins(self, text: str):
        admins = await self.get_all_admins()
        for admin in admins:
            await self.send_text_message(admin, text, False)

    async def send_menu_to_admins(self, menu: NavigationTree, kwargs: dict[str, any]):
        admins = await self.get_all_admins()
        for admin in admins:
            await self.send_menu_to_user(admin, menu, kwargs, False)

    async def send_menu_to_user(
            self,
            user: User | str,
            menu: NavigationTree,
            kwargs: dict[str, any],
            mock: bool = True):
        chat_id = user.telegram_chat_id if isinstance(user, User) else user
        if mock:
            chat_id = try_mock_subj_to_chat_id(user)
        if not chat_id:
            return
        await self._logger.info("sent menu to user", chat_id=chat_id, menu=menu)
        await self._navigation.send_template_to_chat(chat_id, menu, kwargs=kwargs)



