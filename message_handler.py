import logging
import random
from pathlib import Path

from maxapi.types import MessageCreated, Command, BotStarted
from config import MY_TIMEZONE, MESSAGES_FILE, SEND_HOUR, SEND_MINUTE
from bot_state import state
from utils import save_chat_id, load_messages, load_saved_chat_id
from keywords_handler import get_keywords_config, reload_keywords_config, send_keyword_response
from datetime import datetime
from utils import get_chat_id_from_event

logger = logging.getLogger(__name__)


async def ensure_chat_id(event: MessageCreated) -> None:
    """Сохраняет chat_id из события (универсальный способ)"""
    chat_id = get_chat_id_from_event(event)
    if chat_id is None:
        logger.warning("Не удалось получить chat_id, пропускаем")
        return
    
    if state.chat_id != chat_id:
        state.chat_id = chat_id
        save_chat_id(state.chat_id)
        logger.info(f"Сохранён chat_id: {state.chat_id}")


def register_handlers(dp):
    """Регистрирует все обработчики команд"""
    
    @dp.bot_started()
    async def on_bot_started(event: BotStarted):
        chat_id = event.chat_id
        state.chat_id = chat_id
        save_chat_id(chat_id)
        await event.bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован! Теперь каждый день в 9:00 я буду присылать сообщение."
        )
        logger.info(f"Бот активирован через BotStarted в чате {chat_id}")

    @dp.message_created(Command('start'))
    async def cmd_start(event: MessageCreated):
        await ensure_chat_id(event)
        await event.message.answer(
            "✅ Бот активирован!\n\n"
            "Теперь каждый день в 9:00 я буду присылать случайное сообщение.\n\n"
            "📋 **Команды:**\n"
            "/test - тестовое сообщение\n"
            "/add <текст> - добавить сообщение\n"
            "/list - список сообщений\n"
            "/stats - статистика\n"
            "/time - время на сервере\n"
            "/reload - перезагрузить ключевые слова\n\n"
            "💬 **Ключевые слова:**\n"
            "Я также отвечаю на слова: привет, пока, спасибо, как дела, помощь и другие!"
        )
        logger.info(f"Бот активирован в чате {state.chat_id}")

    @dp.message_created(Command('test'))
async def cmd_test(event: MessageCreated):
    try:
        messages = load_messages()
        test_text = random.choice(messages)
        await event.message.answer(f"🧪 Тест:\n\n{test_text}")
        
        # ✅ Используем универсальную функцию
        chat_id = get_chat_id_from_event(event)
        logger.debug(f"Тест отправлен в чат {chat_id}")
    except Exception as e:
        await event.message.answer(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка в /test: {e}")

    @dp.message_created(Command('add'))
    async def cmd_add(event: MessageCreated):
        text = getattr(event.message, 'text', '') or ''
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.message.answer("❌ Использование: /add <текст сообщения>")
            return
        
        new_message = parts[1].strip()
        with MESSAGES_FILE.open('a', encoding='utf-8') as f:
            f.write(f"\n{new_message}")
        
        await event.message.answer(f"✅ Добавлено:\n\n{new_message}")
        logger.info(f"Добавлено сообщение: {new_message[:50]}...")

    @dp.message_created(Command('list'))
    async def cmd_list(event: MessageCreated):
        try:
            messages = load_messages()
            if not messages:
                await event.message.answer("📭 База пуста.")
                return
            
            items = [f"{i}. {msg[:50] + '...' if len(msg) > 50 else msg}" 
                     for i, msg in enumerate(messages, 1)]
            list_text = f"📋 **Сообщения ({len(messages)}):**\n\n" + '\n'.join(items)
            
            if len(list_text) > 4000:
                await event.message.answer(f"📋 Всего сообщений: {len(messages)} (слишком много для списка)")
            else:
                await event.message.answer(list_text)
        except Exception as e:
            await event.message.answer(f"❌ Ошибка: {e}")

    @dp.message_created(Command('stats'))
    async def cmd_stats(event: MessageCreated):
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
            await event.message.answer(stats_text)
        except Exception as e:
            await event.message.answer(f"❌ Ошибка: {e}")

    @dp.message_created(Command('time'))
    async def cmd_time(event: MessageCreated):
        now = datetime.now(MY_TIMEZONE)
        await event.message.answer(f"🕐 {now.strftime('%H:%M:%S %d.%m.%Y')} (по вашему времени)")

    @dp.message_created(Command('reload'))
    async def cmd_reload(event: MessageCreated):
        if state.chat_id is not None and event.message.chat_id != state.chat_id:
            await event.message.answer("❌ У вас нет прав для этой команды.")
            return
        try:
            reload_keywords_config()
            await event.message.answer("✅ Ключевые слова успешно перезагружены из keywords.json!")
        except Exception as e:
            await event.message.answer(f"❌ Ошибка при перезагрузке: {e}")

    @dp.message_created()
    async def handle_keywords(event: MessageCreated):
        text = getattr(event.message, 'text', '') or ''
        text_lower = text.lower().strip()
        
        if text_lower.startswith('/') or len(text_lower) > 100:
            return
        
        responses = get_keywords_config()
        for response in responses:
            keywords_lower = [kw.lower() for kw in response.get("keywords", [])]
            for keyword in keywords_lower:
                if keyword in text_lower:
                    logger.info(f"Сработало ключевое слово '{keyword}' в чате {event.message.chat_id}")
                    await send_keyword_response(event, response)
                    return

    @dp.message_created()
    async def handle_unknown(event: MessageCreated):
        text = getattr(event.message, 'text', '') or ''
        known_commands = ['/start', '/test', '/add', '/list', '/stats', '/time', '/reload']
        if text and text.startswith('/') and text not in known_commands:
            await event.message.answer("❓ Неизвестная команда. Напишите /start для списка команд.")
