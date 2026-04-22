import logging
import random
from pathlib import Path
from typing import Optional

from config import CHAT_ID_FILE, MESSAGES_FILE

# Импортируем асинхронные функции из db.py
from db import (
    add_message_db as add_message,
    load_messages_db as load_messages,
    clear_messages_db as clear_messages,
    get_random_message_db as get_random_message,
    get_messages_count_db as get_messages_count,
    get_messages_total_length_db as get_messages_total_length,
    save_chat_id_db as save_chat_id,
    load_chat_id_db as load_saved_chat_id,
    load_keywords_db as load_keywords,
    get_keywords_count_db as get_keywords_count,
)

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
    """Получение chat_id из события"""
    if hasattr(event, 'chat_id'):
        return event.chat_id
    if hasattr(event, 'message') and hasattr(event.message, 'recipient'):
        if hasattr(event.message.recipient, 'chat_id'):
            return event.message.recipient.chat_id
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
