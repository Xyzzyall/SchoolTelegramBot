from itertools import groupby

import structlog
import telegram.error
from injector import singleton, Injector, inject
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from voice_bot.domain.services.message_builder import MessageBuilder
from voice_bot.telegram_bot.navigation.base_classes import NavigationContext, BaseView, _ButtonStab, NavigationTree, \
    TgContext, _TreeEntry
from voice_bot.telegram_bot.navigation.misc.callback_data_codec import CallbackDataCodec
from voice_bot.telegram_bot.navigation.tg_contexts import UpdateContext, ProxyContext
from voice_bot.telegram_bot.telegram_bot_proxy import TelegramBotProxy
from voice_bot.telegram_di_scope import _TelegramUpdate


@singleton
class Navigation:
    @inject
    def __init__(self, injector: Injector, msg_builder: MessageBuilder, callback_data_codec: CallbackDataCodec,
                 proxy: TelegramBotProxy):
        self._proxy = proxy
        self._callback_data_codec = callback_data_codec
        self._msg_builder = msg_builder
        self._injector = injector
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def process_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.callback_query:
            raise NotImplementedError("Navigation.process_callback only works with callback updates")

        nav_context = self._callback_data_codec.decode(update.callback_query.data)
        if not nav_context:
            await update.callback_query.answer("Данные устарели. Запустите меню ещё раз.")
            return

        tg_context = UpdateContext(update=update, context=context)
        target_entry = await self._walk_down_the_tree(nav_context, tg_context)
        if not target_entry:
            return

        entry_handler = self._injector.get(target_entry.element_type, _TelegramUpdate)
        entry_handler.push_context(nav_context, tg_context, target_entry)
        navigation_context = await entry_handler.handle()

        new_entry = await self._walk_down_the_tree(nav_context, tg_context)
        if not issubclass(new_entry.element_type, BaseView):
            await self._logger.error("Entry handling resulted in navigating to action",
                                     path=navigation_context.tree_path)
            await update.callback_query.answer("Что-то пошло не так")
            return

        msg, buttons = await self._draw_view_entry(new_entry, tg_context, navigation_context)
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
        except telegram.error.BadRequest as bad_request:
            # 'the same message and markup' telegram exception workaround
            if "are exactly the same as a current content" not in bad_request.message:
                raise

    async def process_command(
            self, nav_tree: NavigationTree, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        if not update.effective_message:
            raise NotImplementedError("Navigation.process_command works only in message updates")

        tg_context = UpdateContext(update=update, context=context)
        root = await self._get_root_screen(nav_tree, tg_context)

        if not root:
            return False

        nav_context = NavigationContext(
            root=root,
            tree_path=[],
            kwargs={}
        )

        await self._send_screen_to_context(nav_context, tg_context)
        return True

    async def send_template_to_chat(self, chat_id: str, nav_tree: NavigationTree, **kwargs):
        tg_context = ProxyContext(proxy=self._proxy, chat_id=chat_id)
        root = await self._get_root_screen(nav_tree, tg_context)
        if not root:
            await self._logger.warning(
                "no _TreeEntry is suitable for user",
                chat_id=chat_id,
                nav_tree="{" + ", ".join(str(nav_tree)) + "}")
            return

        nav_context = NavigationContext(
            root=root,
            tree_path=[],
            kwargs=kwargs
        )

        await self._send_screen_to_context(nav_context, tg_context)

    async def _walk_down_the_tree(
            self, navigation_context: NavigationContext, context: TgContext) -> _TreeEntry | None:
        current_entry = navigation_context.root
        for entry_key in navigation_context.tree_path:
            if entry_key not in current_entry.children:
                await self._logger.warning("Invalid navtree path", path=navigation_context.tree_path)
                await context.popup("Что-то пошло не так")
                return None

            current_entry = current_entry.children[entry_key]

            if not await self._check_claims_for_entry(current_entry, context):
                await context.popup("Недостаточно прав")
                return None

        return current_entry

    async def _send_screen_to_context(
            self, navigation_context: NavigationContext, context: TgContext):
        root_entry = navigation_context.root
        message_text, keyboard = await self._draw_view_entry(root_entry, context, navigation_context)
        await context.message(message_text, buttons=keyboard)

    async def _get_root_screen(self, nav_tree: list[_TreeEntry],
                               context: TgContext) -> _TreeEntry | None:
        for screen in nav_tree:
            if not await self._check_claims_for_entry(screen, context):
                continue
            return screen
        return None

    async def _draw_view_entry(
            self, entry: _TreeEntry, context: TgContext, nav_context: NavigationContext
    ) -> (str, list[list[InlineKeyboardButton]]):
        if not issubclass(entry.element_type, BaseView):
            raise NotImplementedError("Only view classes")
        entry_handler = self._injector.get(entry.element_type, _TelegramUpdate)
        entry_handler.push_context(nav_context, context, entry)
        message_text = await entry_handler.get_message_text() if not entry.inner_text_template_override \
            else await self._msg_builder.format(entry.inner_text_template_override)

        button_stabs = await entry_handler.get_view_buttons()
        for key, entry_child in entry.children.items():
            if new_stab := await self._tree_entry_to_button_stab(entry_child, context, nav_context):
                button_stabs[key] = new_stab
        sorted_stabs = [(key, stab) for key, stab in button_stabs.items()]
        sorted_stabs.sort(key=lambda x: x[1].position[0])

        got_keyboard = []
        for _, buttons in groupby(sorted_stabs, key=lambda x: x[1].position[0]):
            buttons_list = list(buttons)
            buttons_list.sort(key=lambda x: x[1].position[1])
            got_keyboard.append([
                InlineKeyboardButton(
                    text=button.title,
                    callback_data=self._callback_data_codec.encode(NavigationContext(
                        root=nav_context.root,
                        tree_path=nav_context.tree_path + ([key] if key[0] != '_' else []),
                        kwargs={**button.kwargs, **nav_context.kwargs}
                    ))
                ) for key, button in buttons_list
            ])
        return message_text, got_keyboard

    async def _tree_entry_to_button_stab(self, entry: _TreeEntry, context: TgContext,
                                         nav_context: NavigationContext) -> _ButtonStab | None:
        if not await self._check_claims_for_entry(entry, context):
            return None
        entry_handler = self._injector.get(entry.element_type, _TelegramUpdate)
        entry_handler.push_context(nav_context, context, entry)
        res = _ButtonStab(
            position=entry.position,
            title=await entry_handler.get_title() if not entry.title_override else entry.title_override,
            kwargs=nav_context.kwargs
        )
        return res

    async def _check_claims_for_entry(
            self, entry: _TreeEntry, context: TgContext
    ) -> bool:
        for claim in entry.claims:
            if not await self._injector.get(claim.base_class, _TelegramUpdate).check(
                    context.get_chat_id(),
                    claim
            ):
                return False
        return True
