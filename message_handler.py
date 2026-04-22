import logging
import random
from datetime import datetime

from maxapi.types import MessageCreated, Command, BotStarted

from config import MY_TIMEZONE, MESSAGES_FILE, SEND_HOUR, SEND_MINUTE
from bot_state import state
from utils import save_chat_id, load_messages
from keywords_handler import get_keywords_config, reload_keywords_config, send_keyword_response
from keyboards import get_main_keyboard, get_cancel_keyboard

logger = logging.getLogger(__name__)


# Состояния для добавления сообщения
user_states = {}  # chat_id -> state

async def ensure_chat_id(event: MessageCreated) -> None:
    """Сохраняет chat_id из события"""
    if hasattr(event, 'chat_id'):
        chat_id = event.chat_id
    else:
        logger.warning("Не удалось получить chat_id из event.chat_id")
        return
    
    if state.chat_id != chat_id:
        state.chat_id = chat_id
        save_chat_id(state.chat_id)
        logger.info(f"Сохранён chat_id: {state.chat_id}")


def register_handlers(dp):
    
    @dp.bot_started()
    async def on_bot_started(event: BotStarted):
        chat_id = event.chat_id
        state.chat_id = chat_id
        save_chat_id(chat_id)
        
        keyboard = get_main_keyboard()
        await event.bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован! Теперь каждый день в 12:30 я буду присылать сообщение.\n\nИспользуйте кнопки для управления:",
            reply_markup=keyboard
        )
        logger.info(f"Бот активирован через BotStarted в чате {chat_id}")

    @dp.message_created(Command('start'))
    async def cmd_start(event: MessageCreated):
        await ensure_chat_id(event)
        
        keyboard = get_main_keyboard()
        await event.message.answer(
            "✅ Бот активирован!\n\n"
            "Теперь каждый день в 12:30 я буду присылать случайное сообщение.\n\n"
            "**Используйте кнопки для управления:**\n"
            "📝 **Тест** - отправить тестовое сообщение\n"
            "➕ **Добавить** - добавить новое сообщение\n"
            "📋 **Список** - показать все сообщения\n"
            "📊 **Статистика** - статистика бота\n"
            "🕐 **Время** - текущее время на сервере\n"
            "🔄 **Перезагрузить** - перезагрузить ключевые слова\n\n"
            "💬 **Ключевые слова:**\n"
            "Я также отвечаю на слова: привет, пока, спасибо, как дела, помощь и другие!",
            reply_markup=keyboard
        )
        logger.info(f"Бот активирован в чате {state.chat_id}")

    # Обработчик текстовых кнопок и команд
    @dp.message_created()
    async def handle_button_presses(event: MessageCreated):
        text = event.message.body.text if event.message.body else ''
        
        # Обработка команд (для обратной совместимости)
        if text == '/test':
            await cmd_test(event)
        elif text == '/add':
            await cmd_add_prompt(event)
        elif text == '/list':
            await cmd_list(event)
        elif text == '/stats':
            await cmd_stats(event)
        elif text == '/time':
            await cmd_time(event)
        elif text == '/reload':
            await cmd_reload(event)
        # Обработка кнопок
        elif text == "📝 Тест":
            await cmd_test(event)
        elif text == "➕ Добавить":
            await cmd_add_prompt(event)
        elif text == "📋 Список":
            await cmd_list(event)
        elif text == "📊 Статистика":
            await cmd_stats(event)
        elif text == "🕐 Время":
            await cmd_time(event)
        elif text == "🔄 Перезагрузить":
            await cmd_reload(event)
        elif text == "❌ Отмена":
            user_states.pop(event.chat_id, None)
            keyboard = get_main_keyboard()
            await event.message.answer("❌ Операция отменена", reply_markup=keyboard)

    async def cmd_test(event: MessageCreated):
        try:
            messages = load_messages()
            if not messages:
                await event.message.answer("❌ Нет сообщений в базе. Добавьте хотя бы одно сообщение командой /add")
                return
            test_text = random.choice(messages)
            await event.message.answer(f"🧪 **Тест:**\n\n{test_text}")
            logger.debug(f"Тест отправлен в чат {event.chat_id}")
        except Exception as e:
            await event.message.answer(f"❌ Ошибка: {e}")
            logger.error(f"Ошибка в /test: {e}")

    async def cmd_add_prompt(event: MessageCreated):
        """Запрашивает текст для добавления"""
        user_states[event.chat_id] = "waiting_for_message"
        keyboard = get_cancel_keyboard()
        await event.message.answer(
            "✏️ Введите текст сообщения для добавления:\n\n"
            "(или нажмите ❌ Отмена)",
            reply_markup=keyboard
        )

    async def cmd_add(event: MessageCreated, text: str):
        """Добавляет сообщение в базу"""
        new_message = text.strip()
        if not new_message:
            await event.message.answer("❌ Сообщение не может быть пустым")
            return
        
        # Добавляем сообщение в файл
        with MESSAGES_FILE.open('a', encoding='utf-8') as f:
            f.write(f"{new_message}\n")
        
        keyboard = get_main_keyboard()
        await event.message.answer(
            f"✅ **Добавлено:**\n\n{new_message}",
            reply_markup=keyboard
        )
        logger.info(f"Добавлено сообщение: {new_message[:50]}...")
        
        # Очищаем состояние
        user_states.pop(event.chat_id, None)

    async def cmd_list(event: MessageCreated):
        try:
            messages = load_messages()
            if not messages:
                await event.message.answer("📭 База пуста. Добавьте сообщения через /add")
                return
            
            # Показываем первые 10 сообщений, чтобы не было слишком длинного сообщения
            if len(messages) > 10:
                items = [f"{i}. {msg[:50] + '...' if len(msg) > 50 else msg}" 
                         for i, msg in enumerate(messages[:10], 1)]
                list_text = f"📋 **Сообщения (первые 10 из {len(messages)}):**\n\n" + '\n'.join(items)
                list_text += f"\n\n📌 Всего сообщений: {len(messages)}"
            else:
                items = [f"{i}. {msg[:50] + '...' if len(msg) > 50 else msg}" 
                         for i, msg in enumerate(messages, 1)]
                list_text = f"📋 **Сообщения ({len(messages)}):**\n\n" + '\n'.join(items)
            
            await event.message.answer(list_text)
        except Exception as e:
            await event.message.answer(f"❌ Ошибка: {e}")

    async def cmd_stats(event: MessageCreated):
        try:
            messages = load_messages()
            total = len(messages)
            avg_len = sum(len(m) for m in messages) // total if total else 0
            size_kb = MESSAGES_FILE.stat().st_size / 1024 if MESSAGES_FILE.exists() else 0
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
            await event.message.answer(stats_text)
        except Exception as e:
            await event.message.answer(f"❌ Ошибка: {e}")

    async def cmd_time(event: MessageCreated):
        now = datetime.now(MY_TIMEZONE)
        await event.message.answer(f"🕐 {now.strftime('%H:%M:%S %d.%m.%Y')}")

    async def cmd_reload(event: MessageCreated):
        """Перезагружает ключевые слова из JSON файла"""
        current_chat_id = event.chat_id if hasattr(event, 'chat_id') else None
        
        if state.chat_id is not None and current_chat_id != state.chat_id:
            await event.message.answer("❌ У вас нет прав для этой команды.")
            return
        
        try:
            reload_keywords_config()
            keyboard = get_main_keyboard()
            await event.message.answer("✅ Ключевые слова успешно перезагружены из keywords.json!", reply_markup=keyboard)
        except Exception as e:
            await event.message.answer(f"❌ Ошибка при перезагрузке: {e}")

    # Обработчик для добавления сообщения (ожидание ввода)
    @dp.message_created()
    async def handle_message_input(event: MessageCreated):
        text = event.message.body.text if event.message.body else ''
        
        # Проверяем, ожидаем ли мы ввод сообщения
        if event.chat_id in user_states and user_states[event.chat_id] == "waiting_for_message":
            if text == "❌ Отмена":
                user_states.pop(event.chat_id, None)
                keyboard = get_main_keyboard()
                await event.message.answer("❌ Добавление отменено", reply_markup=keyboard)
            else:
                await cmd_add(event, text)

    # Обработчик ключевых слов
    @dp.message_created()
    async def handle_keywords(event: MessageCreated):
        """Отвечает на сообщения по ключевым словам"""
        text = event.message.body.text if event.message.body else ''
        text_lower = text.lower().strip()
        
        # Игнорируем команды и кнопки
        buttons = ["📝 тест", "➕ добавить", "📋 список", "📊 статистика", "🕐 время", "🔄 перезагрузить", "❌ отмена"]
        if text_lower.startswith('/') or text_lower in buttons or text in buttons:
            return
        
        # Игнорируем слишком длинные сообщения
        if len(text_lower) > 100:
            return
        
        # Загружаем конфигурацию
        responses = get_keywords_config()
        
        # Ищем подходящий ответ
        for response in responses:
            keywords = response.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    logger.info(f"Сработало ключевое слово '{keyword}' в чате {event.chat_id}")
                    await send_keyword_response(event, response)
                    return

    # Обработчик неизвестных команд
    @dp.message_created()
    async def handle_unknown(event: MessageCreated):
        text = event.message.body.text if event.message.body else ''
        known_buttons = ["📝 Тест", "➕ Добавить", "📋 Список", "📊 Статистика", "🕐 Время", "🔄 Перезагрузить", "❌ Отмена"]
        
        # Если это неизвестная команда, но не кнопка
        if text and text.startswith('/') and text not in ['/start', '/test', '/add', '/list', '/stats', '/time', '/reload']:
            keyboard = get_main_keyboard()
            await event.message.answer(
                "❓ Неизвестная команда.\n\nИспользуйте кнопки для управления ботом:",
                reply_markup=keyboard
            )
