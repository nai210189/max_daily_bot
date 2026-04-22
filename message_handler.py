import logging
import random
from datetime import datetime

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, Command, BotStarted

from config import MY_TIMEZONE, MESSAGES_FILE, SEND_HOUR, SEND_MINUTE
from bot_state import state
from utils import save_chat_id, load_messages, add_message, clear_messages
from keywords_handler import get_keywords_config, reload_keywords_config, send_keyword_response
from keyboards import (
    get_main_reply_keyboard,
    get_remove_keyboard,
    get_simple_reply_keyboard,
    get_action_for_button
)

logger = logging.getLogger(__name__)


def get_chat_id(event) -> int | None:
    """Получает chat_id из события"""
    # Прямой доступ из лога: event.chat.chat_id
    if hasattr(event, 'chat') and hasattr(event.chat, 'chat_id'):
        return event.chat.chat_id
    # Альтернативный способ
    if hasattr(event, 'chat_id'):
        return event.chat_id
    # Для BotStarted
    if hasattr(event, 'chat_id'):
        return event.chat_id
    logger.warning(f"Не удалось получить chat_id из {type(event)}")
    return None


def register_handlers(dp: Dispatcher, bot: Bot):
    
    @dp.bot_started()
    async def on_bot_started(event: BotStarted):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в on_bot_started")
            return
        
        state.chat_id = chat_id
        save_chat_id(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован! Теперь каждый день я буду присылать сообщение.\n\nОтправьте /menu для управления."
        )
        logger.info(f"Бот активирован через BotStarted в чате {chat_id}")

    @dp.message_created(Command('start'))
    async def cmd_start(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /start")
            return
        
        state.chat_id = chat_id
        save_chat_id(chat_id)
        
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован!\n\n"
                 "Теперь каждый день я буду присылать случайное сообщение.\n\n"
                 "📋 **Команды:**\n"
                 "/test - тестовое сообщение\n"
                 "/add <текст> - добавить сообщение\n"
                 "/list - список сообщений\n"
                 "/stats - статистика\n"
                 "/time - время на сервере\n"
                 "/reload - перезагрузить ключевые слова\n"
                 "/menu - показать меню\n\n"
                 "💬 **Ключевые слова:**\n"
                 "Я отвечаю на слова: привет, пока, спасибо, как дела!",
            parse_mode="markdown"
        )
        logger.info(f"Бот активирован в чате {chat_id}")

    @dp.message_created(Command('menu'))
    async def cmd_menu(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /menu")
            return
        
        keyboard = get_main_reply_keyboard()
        await bot.send_message(
            chat_id=chat_id,
            text="🔧 **Панель управления**\n\nНажмите на кнопку:",
            reply_markup=keyboard,
            parse_mode="markdown"
        )
        logger.info(f"Меню показано в чате {chat_id}")

    @dp.message_created(Command('hide_menu'))
    async def cmd_hide_menu(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /hide_menu")
            return
        
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Клавиатура скрыта. Отправьте /menu чтобы показать снова.",
            reply_markup=get_remove_keyboard()
        )
        logger.info(f"Клавиатура скрыта в чате {chat_id}")

    @dp.message_created(Command('test'))
    async def cmd_test(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /test")
            return
        
        try:
            messages = load_messages()
            test_text = random.choice(messages)
            await bot.send_message(chat_id=chat_id, text=f"🧪 Тест:\n\n{test_text}")
            logger.debug(f"Тест отправлен в чат {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка в /test: {e}")
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")

    @dp.message_created(Command('add'))
    async def cmd_add(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /add")
            return
        
        text = event.message.body.text if event.message.body else ''
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2 or not parts[1].strip():
            await bot.send_message(chat_id=chat_id, text="❌ Использование: /add <текст сообщения>")
            return
        
        new_message = parts[1].strip()
        add_message(new_message)
        await bot.send_message(chat_id=chat_id, text=f"✅ Добавлено:\n\n{new_message}")
        logger.info(f"Добавлено сообщение: {new_message[:50]}...")

    @dp.message_created(Command('list'))
    async def cmd_list(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /list")
            return
        
        try:
            messages = load_messages()
            if not messages:
                await bot.send_message(chat_id=chat_id, text="📭 База пуста.")
                return
            
            items = [f"{i}. {msg[:50] + '...' if len(msg) > 50 else msg}" 
                     for i, msg in enumerate(messages, 1)]
            list_text = f"📋 **Сообщения ({len(messages)}):**\n\n" + '\n'.join(items)
            
            if len(list_text) > 4000:
                await bot.send_message(chat_id=chat_id, text=f"📋 Всего сообщений: {len(messages)}")
            else:
                await bot.send_message(chat_id=chat_id, text=list_text, parse_mode="markdown")
        except Exception as e:
            logger.error(f"Ошибка в /list: {e}")
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")

    @dp.message_created(Command('stats'))
    async def cmd_stats(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /stats")
            return
        
        try:
            messages = load_messages()
            total = len(messages)
            avg_len = sum(len(m) for m in messages) // total if total else 0
            size_kb = MESSAGES_FILE.stat().st_size / 1024
            keywords_count = len(get_keywords_config())
            
            stats_text = (
                f"📊 **Статистика**\n\n"
                f"• Сообщений в базе: {total}\n"
                f"• Средняя длина: {avg_len} симв.\n"
                f"• Размер файла: {size_kb:.1f} KB\n"
                f"• Время отправки: {SEND_HOUR:02d}:{SEND_MINUTE:02d}\n"
                f"• Ключевых слов (наборов): {keywords_count}\n"
                f"• Чат: {'активирован' if state.chat_id else 'не активирован'}"
            )
            await bot.send_message(chat_id=chat_id, text=stats_text, parse_mode="markdown")
        except Exception as e:
            logger.error(f"Ошибка в /stats: {e}")
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")

    @dp.message_created(Command('time'))
    async def cmd_time(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /time")
            return
        
        now = datetime.now(MY_TIMEZONE)
        await bot.send_message(chat_id=chat_id, text=f"🕐 {now.strftime('%H:%M:%S %d.%m.%Y')}")

    @dp.message_created(Command('reload'))
    async def cmd_reload(event: MessageCreated):
        chat_id = get_chat_id(event)
        if not chat_id:
            logger.warning("Не удалось получить chat_id в /reload")
            return
        
        if state.chat_id is not None and chat_id != state.chat_id:
            await bot.send_message(chat_id=chat_id, text="❌ У вас нет прав для этой команды.")
            return
        
        try:
            reload_keywords_config()
            await bot.send_message(chat_id=chat_id, text="✅ Ключевые слова успешно перезагружены!")
        except Exception as e:
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка при перезагрузке: {e}")

    # ===== ОБРАБОТЧИК КЛЮЧЕВЫХ СЛОВ =====
    @dp.message_created()
    async def handle_keywords(event: MessageCreated):
        text = event.message.body.text if event.message.body else ''
        text_lower = text.lower().strip()
        
        if text_lower.startswith('/'):
            return
        
        if len(text_lower) > 100:
            return
        
        responses = get_keywords_config()
        for response in responses:
            keywords = response.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    logger.info(f"Сработало ключевое слово '{keyword}'")
                    await send_keyword_response(event, response, bot)
                    return

    # ===== ОБРАБОТЧИК REPLY-КНОПОК =====
    @dp.message_created()
    async def handle_reply_buttons(event: MessageCreated):
        text = event.message.body.text if event.message.body else ''
        chat_id = get_chat_id(event)
        
        if not chat_id:
            return
        
        action = get_action_for_button(text)
        if action is None:
            return
        
        logger.info(f"Нажата кнопка: '{text}' -> {action}")
        
        if action.startswith('/'):
            if action == '/stats':
                await cmd_stats(event)
            elif action == '/list':
                await cmd_list(event)
            elif action == '/test':
                await cmd_test(event)
            elif action == '/time':
                await cmd_time(event)
            elif action == '/reload':
                await cmd_reload(event)
        elif action == "action_add":
            await bot.send_message(
                chat_id=chat_id,
                text="✏️ Введите текст нового сообщения:",
                reply_markup=get_simple_reply_keyboard()
            )
        elif action == "action_confirm_yes":
            clear_messages()
            await bot.send_message(
                chat_id=chat_id,
                text="✅ База сообщений очищена!",
                reply_markup=get_remove_keyboard()
            )
        elif action == "action_close":
            await cmd_hide_menu(event)

    # ===== НЕИЗВЕСТНЫЕ КОМАНДЫ =====
    @dp.message_created()
    async def handle_unknown(event: MessageCreated):
        text = event.message.body.text if event.message.body else ''
        known_commands = ['/start', '/test', '/add', '/list', '/stats', '/time', '/reload', '/menu', '/hide_menu']
        if text and text.startswith('/') and text not in known_commands:
            chat_id = get_chat_id(event)
            if chat_id:
                await bot.send_message(chat_id=chat_id, text="❓ Неизвестная команда. Напишите /start для списка команд.")
