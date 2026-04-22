import logging
import random
from pathlib import Path

from config import CHAT_ID_FILE, MESSAGES_FILE

logger = logging.getLogger(__name__)


# ===== РАБОТА С CHAT_ID =====
def save_chat_id(chat_id: int) -> None:
    """Сохраняет chat_id в файл"""
    CHAT_ID_FILE.write_text(str(chat_id), encoding='utf-8')


def load_saved_chat_id() -> int | None:
    """Загружает сохранённый chat_id из файла"""
    if CHAT_ID_FILE.exists():
        try:
            return int(CHAT_ID_FILE.read_text(encoding='utf-8').strip())
        except (ValueError, OSError):
            logger.warning("Не удалось прочитать сохранённый chat_id")
    return None


def get_chat_id_from_event(event) -> int | None:
    """
    Универсальное получение chat_id из события.
    Для maxapi 1.0.0 chat_id может быть в разных местах.
    """
    # Пробуем разные варианты
    
    # Вариант 1: напрямую из события (самый вероятный)
    if hasattr(event, 'chat_id'):
        return event.chat_id
    
    # Вариант 2: из event.message
    if hasattr(event, 'message'):
        if hasattr(event.message, 'chat_id'):
            return event.message.chat_id
        if hasattr(event.message, 'chat') and hasattr(event.message.chat, 'id'):
            return event.message.chat.id
    
    # Вариант 3: через атрибуты __dict__
    if hasattr(event, '__dict__') and 'chat_id' in event.__dict__:
        return event.__dict__['chat_id']
    
    # Вариант 4: если событие - это словарь
    if isinstance(event, dict) and 'chat_id' in event:
        return event['chat_id']
    
    # Если ничего не нашли, логируем для отладки
    logger = logging.getLogger(__name__)
    logger.error(f"Не удалось получить chat_id. Доступные атрибуты: {[a for a in dir(event) if not a.startswith('_')]}")
    
    return None


# ===== РАБОТА С БАЗОЙ СООБЩЕНИЙ =====
def _create_example_messages() -> None:
    """Создаёт файл с примерами сообщений"""
    example_messages = [
        "Доброе утро! Хорошего дня! ☀️",
        "Не забывайте пить воду 💧",
        "Сегодня отличный день для новых свершений! 🚀",
        "Улыбнитесь, это бесплатно 😊",
        "Среда — маленькая пятница! 🎉"
    ]
    MESSAGES_FILE.write_text('\n'.join(example_messages), encoding='utf-8')
    logger.info(f"Создан файл {MESSAGES_FILE} с примерами сообщений")


def load_messages() -> list[str]:
    """Загружает сообщения из текстового файла"""
    if not MESSAGES_FILE.exists():
        _create_example_messages()
    
    content = MESSAGES_FILE.read_text(encoding='utf-8')
    messages = [line.strip() for line in content.splitlines() if line.strip()]
    
    if not messages:
        raise ValueError(f"Файл {MESSAGES_FILE} пуст!")
    
    return messages


def add_message(text: str) -> None:
    """Добавляет новое сообщение в базу"""
    with MESSAGES_FILE.open('a', encoding='utf-8') as f:
        f.write(f"\n{text}")
    logger.info(f"Добавлено сообщение: {text[:50]}...")


def clear_messages() -> None:
    """Очищает базу сообщений"""
    MESSAGES_FILE.write_text('', encoding='utf-8')
    logger.info("База сообщений очищена")


def get_random_message(messages: list[str]) -> str:
    """Возвращает случайное сообщение из списка"""
    return random.choice(messages)
