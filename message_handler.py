import logging
import random
from datetime import datetime

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, Command, BotStarted

from config import MY_TIMEZONE, MESSAGES_FILE, SEND_HOUR, SEND_MINUTE
from bot_state import state
from utils import save_chat_id, load_messages, add_message, clear_messages, get_chat_id_from_event, load_saved_chat_id
from keywords_handler import get_keywords_config, reload_keywords_config, send_keyword_response
from keyboards import (
    get_main_reply_keyboard, 
    get_remove_keyboard, 
    get_simple_reply_keyboard,
    get_action_for_button
)
from scheduler import get_next_run_time

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher, bot: Bot):
    """Регистрирует все обработчики команд"""
    
    # ===== ВСТРОЕННЫЕ СОБЫТИЯ =====
    
    @dp.bot_started()
    async def on_bot_started(event: BotStarted):
        """Пользователь нажал 'Начать'"""
        chat_id = event.chat_id
        state.chat_id = chat_id
        save_chat_id(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован! Теперь каждый день в 9:00 я буду присылать сообщение.\n\nОтправьте /menu для управления."
        )
        logger.info(f"Бот активирован в чате {chat_id}")
    
    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    
    @dp.message_created(Command('start'))
    async def cmd_start(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /start")
            return
        
        if chat_id:
            state.chat_id = chat_id
            save_chat_id(chat_id)
        
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован!\n\n"
                 "Теперь каждый день в 9:00 я буду присылать случайное сообщение.\n\n"
                 "📋 **Команды:**\n"
                 "/test - тестовое сообщение\n"
                 "/add <текст> - добавить сообщение\n"
                 "/list - список сообщений\n"
                 "/stats - статистика\n"
                 "/time - время на сервере\n"
                 "/reload - перезагрузить ключевые слова\n"
                 "/menu - показать меню\n\n"
                 "💬 Я также отвечаю на слова: привет, пока, спасибо, как дела!",
            parse_mode="markdown"
        )
        logger.info(f"Бот активирован в чате {chat_id}")
    
    @dp.message_created(Command('menu'))
    async def cmd_menu(event: MessageCreated):
        """Показывает reply-клавиатуру"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /menu")
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
        """Скрывает клавиатуру"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /hide_menu")
            return
        
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Клавиатура скрыта. Отправьте /menu чтобы показать снова.",
            reply_markup=get_remove_keyboard()
        )
        logger.info(f"Клавиатура скрыта в чате {chat_id}")
    
    @dp.message_created(Command('test'))
    async def cmd_test(event: MessageCreated):
        """Тестовое сообщение"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /test")
            return
        
        try:
            messages = load_messages()
            test_text = random.choice(messages)
            await bot.send_message(chat_id=chat_id, text=f"🧪 Тест:\n\n{test_text}")
            logger.debug(f"Тест отправлен в чат {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка в /test: {e}")
            if chat_id:
                await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")
    
    @dp.message_created(Command('add'))
    async def cmd_add(event: MessageCreated):
        """Добавляет сообщение в базу"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /add")
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
        """Список сообщений"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /list")
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
            if chat_id:
                await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")
    
    @dp.message_created(Command('stats'))
    async def cmd_stats(event: MessageCreated):
        """Статистика"""
        chat_id = get_chat_id_from_event(event)
        
        # Проверка: если chat_id не получен, выходим
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /stats")
            return
        
        try:
            messages = load_messages()
            total = len(messages)
            avg_len = sum(len(m) for m in messages) // total if total else 0
            size_kb = MESSAGES_FILE.stat().st_size / 1024
            keywords_count = len(get_keywords_config())
            
            stats_text = (
                f"📊 **Статистика**\n\n"
                f"• Сообщений: {total}\n"
                f"• Средняя длина: {avg_len} симв.\n"
                f"• Размер файла: {size_kb:.1f} KB\n"
                f"• Время отправки: {SEND_HOUR:02d}:{SEND_MINUTE:02d}\n"
                f"• Ключевых слов: {keywords_count}\n"
                f"• Чат: {'активирован' if state.chat_id else 'не активирован'}"
            )
            await bot.send_message(chat_id=chat_id, text=stats_text, parse_mode="markdown")
        except Exception as e:
            logger.error(f"Ошибка в /stats: {e}")
            if chat_id:
                await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")
    
    @dp.message_created(Command('time'))
    async def cmd_time(event: MessageCreated):
        """Текущее время"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /time")
            return
        
        now = datetime.now(MY_TIMEZONE)
        await bot.send_message(chat_id=chat_id, text=f"🕐 {now.strftime('%H:%M:%S %d.%m.%Y')} (по вашему времени)")
    
    @dp.message_created(Command('next'))
    async def cmd_next(event: MessageCreated):
        """Следующая отправка"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /next")
            return
        
        next_time = get_next_run_time()
        now = datetime.now(MY_TIMEZONE)
        wait_minutes = int((next_time - now).total_seconds() / 60)
        
        await bot.send_message(
            chat_id=chat_id,
            text=f"⏰ **Следующая отправка:**\n\n"
                 f"• Время: {next_time.strftime('%H:%M:%S %d.%m.%Y')}\n"
                 f"• Через: {wait_minutes} минут",
            parse_mode="markdown"
        )
    
    @dp.message_created(Command('reload'))
    async def cmd_reload(event: MessageCreated):
        """Перезагружает ключевые слова"""
        chat_id = get_chat_id_from_event(event)
        
        if not chat_id:
            logger.warning("Не удалось получить chat_id для команды /reload")
            return
        
        if state.chat_id is not None and chat_id != state.chat_id:
            await bot.send_message(chat_id=chat_id, text="❌ У вас нет прав для этой команды.")
            return
        
        try:
            reload_keywords_config()
            await bot.send_message(chat_id=chat_id, text="✅ Ключевые слова перезагружены!")
        except Exception as e:
            await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")
    
    # ===== ЕДИНЫЙ ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ =====
    
    @dp.message_created()
    async def handle_text_messages(event: MessageCreated):
        """
        Единый обработчик для всех текстовых сообщений:
        - сначала проверяем кнопки
        - потом ключевые слова
        """
        text = event.message.body.text if event.message.body else ''
        text_lower = text.lower().strip()
        chat_id = get_chat_id_from_event(event)
        
        if not text:
            return
        
        # 1. ПРОВЕРКА НА КНОПКИ (reply-клавиатура)
        action = get_action_for_button(text)
        if action:
            logger.info(f"Нажата кнопка: '{text}' -> {action}")
            
            if action.startswith('/'):
                # Вызываем соответствующую команду
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
                elif action == '/next':
                    await cmd_next(event)
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
                logger.info(f"База очищена в чате {chat_id}")
            elif action == "action_close":
                await cmd_hide_menu(event)
            return  # Кнопка обработана, дальше не идём
        
        # 2. ПРОВЕРКА НА КЛЮЧЕВЫЕ СЛОВА (только если не команда)
        if not text_lower.startswith('/') and len(text_lower) <= 100:
            responses = get_keywords_config()
            for response in responses:
                keywords = response.get("keywords", [])
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        logger.info(f"Сработало ключевое слово '{keyword}' в чате {chat_id}")
                        await send_keyword_response(event, response, bot)
                        return  # Ключевое слово обработано
    
    # ===== НЕИЗВЕСТНЫЕ КОМАНДЫ =====
    
    @dp.message_created()
    async def handle_unknown(event: MessageCreated):
        text = event.message.body.text if event.message.body else ''
        known_commands = ['/start', '/test', '/add', '/list', '/stats', '/time', '/reload', '/menu', '/hide_menu', '/next']
        if text and text.startswith('/') and text not in known_commands:
            chat_id = get_chat_id_from_event(event)
            await bot.send_message(chat_id=chat_id, text="❓ Неизвестная команда. Напишите /start для списка команд.")
