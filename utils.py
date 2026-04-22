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
        raise ValueError(f"Файл {MESSAGES_FILE} пуст! Добавьте хотя бы одно сообщение.")
    
    return messages


# ===== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ CHAT_ID =====
def get_chat_id_from_event(event) -> int | None:
    """
    Универсальное получение chat_id из события.
    Адаптировано под вашу версию библиотеки maxapi.
    """
    # Вариант 1: через event.message.chat.id (основной способ)
    if hasattr(event, 'message') and hasattr(event.message, 'chat'):
        if hasattr(event.message.chat, 'id'):
            return event.message.chat.id
    
    # Вариант 2: для BotStarted
    if hasattr(event, 'chat_id'):
        return event.chat_id
    
    # Вариант 3: через event.chat.id
    if hasattr(event, 'chat') and hasattr(event.chat, 'id'):
        return event.chat.id
    
    # Логируем ошибку для отладки
    logger = logging.getLogger(__name__)
    logger.error(f"Не удалось получить chat_id. event: {type(event)}")
    if hasattr(event, 'message'):
        logger.error(f"event.message атрибуты: {dir(event.message)}")
    
    return None


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
