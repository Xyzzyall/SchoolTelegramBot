from itertools import groupby

import structlog
import telegram.error
from injector import singleton, Injector, inject
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from voice_bot.services.message_builder import MessageBuilder
from voice_bot.telegram_bot.navigation.base_classes import NavigationContext, BaseView, _ButtonStab, NavigationTree
from voice_bot.telegram_bot.navigation.misc.callback_data_codec import CallbackDataCodec
from voice_bot.telegram_bot.navigation.nav_tree import _TreeEntry
from voice_bot.telegram_di_scope import _TelegramUpdate


@singleton
class Navigation:
    @inject
    def __init__(self, injector: Injector, msg_builder: MessageBuilder, callback_data_codec: CallbackDataCodec):
        self._callback_data_codec = callback_data_codec
        self._msg_builder = msg_builder
        self._injector = injector
        self._logger = structlog.get_logger(class_name=__class__.__name__)

    async def process_callback(self, navigation_context: NavigationContext, nav_tree: NavigationTree,
                               update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not navigation_context:
            await update.callback_query.answer("Данные устарели. Запустите меню ещё раз.")
            return
        if not update.callback_query:
            raise NotImplementedError("Navigation.process_callback only works with callback updates")
        target_entry = await self._walk_down_the_tree(navigation_context, nav_tree, update, context)
        if not target_entry:
            return
        entry_handler = self._injector.get(target_entry.element_type, _TelegramUpdate)
        entry_handler.push_context(navigation_context, update, context)
        navigation_context = await entry_handler.handle()
        new_entry = await self._walk_down_the_tree(navigation_context, nav_tree, update, context)
        if not issubclass(new_entry.element_type, BaseView):
            await self._logger.aerror("Entry handling resulted in navigating to no view",
                                      path=navigation_context.tree_path)
            await update.callback_query.answer("Что-то пошло не так")
            return
        msg, buttons = await self._draw_view_entry(new_entry, update, context, navigation_context)
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
        except telegram.error.BadRequest as bad_request:
            # 'the same message and markup' telegram exception workaround
            if "are exactly the same as a current content" not in bad_request.message:
                raise

    async def _walk_down_the_tree(self, navigation_context: NavigationContext, nav_tree: NavigationTree,
                                  update: Update, context: ContextTypes.DEFAULT_TYPE) -> _TreeEntry | None:
        current_entry = await self._get_root_screen(nav_tree, update, context)
        for entry_key in navigation_context.tree_path:
            if entry_key not in current_entry.children:
                await self._logger.awarning("Invalid navtree path", path=navigation_context.tree_path)
                await update.callback_query.answer("Что-то пошло не так")
                return None
            current_entry = current_entry.children[entry_key]
            if not await self._check_claims_for_entry(current_entry, update, context):
                await update.callback_query.answer("Недостаточно прав")
                return None
        navigation_context.context_vars = current_entry.context_vars
        return current_entry

    async def show_root_screen(self, navigation_context: NavigationContext, nav_tree: NavigationTree,
                               update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_message:
            raise NotImplementedError("Navigation.show_root_screen works only in message updates")
        root_entry = await self._get_root_screen(nav_tree, update, context)
        message_text, keyboard = await self._draw_view_entry(root_entry, update, context, navigation_context)
        await update.effective_message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _get_root_screen(self, nav_tree: list[_TreeEntry],
                               update: Update, context: ContextTypes.DEFAULT_TYPE) -> _TreeEntry | None:
        for screen in nav_tree:
            if not await self._check_claims_for_entry(screen, update, context):
                continue
            return screen
        return None

    async def _draw_view_entry(
            self, entry: _TreeEntry, update: Update, context: ContextTypes.DEFAULT_TYPE,
            nav_context: NavigationContext
    ) -> (str, list[list[InlineKeyboardButton]]):
        if not issubclass(entry.element_type, BaseView):
            raise NotImplementedError("Only view classes")
        entry_handler = self._injector.get(entry.element_type, _TelegramUpdate)
        entry_handler.push_context(nav_context, update, context)
        message_text = await entry_handler.get_message_text() if not entry.inner_text_template_override \
            else await self._msg_builder.format(entry.inner_text_template_override)

        button_stabs = await entry_handler.get_view_buttons()
        for key, entry_child in entry.children.items():
            if new_stab := await self._tree_entry_to_button_stab(entry_child, update, context, nav_context):
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
                        tree_path=nav_context.tree_path + ([key] if key[0] != '_' else []),
                        root_cmd=nav_context.root_cmd,
                        context_vars={},
                        kwargs=button.kwargs
                    ))
                ) for key, button in buttons_list
            ])
        return message_text, got_keyboard

    async def _tree_entry_to_button_stab(self, entry: _TreeEntry, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                         nav_context: NavigationContext = None) -> _ButtonStab | None:
        if not await self._check_claims_for_entry(entry, update, context):
            return None
        entry_handler = self._injector.get(entry.element_type, _TelegramUpdate)
        context_vars_buffer = nav_context.context_vars
        nav_context.context_vars = entry.context_vars
        entry_handler.push_context(nav_context, update, context)
        res = _ButtonStab(
            position=entry.position,
            title=await entry_handler.get_title() if not entry.title_override else entry.title_override
        )
        nav_context.context_vars = context_vars_buffer
        return res

    async def _check_claims_for_entry(
            self, entry: _TreeEntry, update: Update,
            context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        for claim in entry.claims:
            if not await self._injector.get(claim, _TelegramUpdate).handle(update, context):
                return False
        return True