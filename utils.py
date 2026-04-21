import logging
from pathlib import Path

from config import CHAT_ID_FILE, MESSAGES_FILE

logger = logging.getLogger(__name__)

# ===== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ CHAT_ID =====
def get_chat_id_from_event(event) -> int | None:
    """
    Универсальное получение chat_id из события.
    Работает с разными версиями библиотеки maxapi.
    
    Пробует последовательно:
    1. event.chat_id
    2. event.message.chat_id  
    3. event.message.chat.id
    """
    # Вариант 1: chat_id напрямую в событии
    if hasattr(event, 'chat_id'):
        return event.chat_id
    
    # Вариант 2: chat_id в event.message
    if hasattr(event, 'message'):
        if hasattr(event.message, 'chat_id'):
            return event.message.chat_id
        if hasattr(event.message, 'chat') and hasattr(event.message.chat, 'id'):
            return event.message.chat.id
    
    # Если ничего не нашли, логируем ошибку для отладки
    logger = logging.getLogger(__name__)
    logger.error(f"Не удалось получить chat_id из события. Доступные атрибуты: {dir(event)}")
    if hasattr(event, 'message'):
        logger.error(f"Атрибуты event.message: {dir(event.message)}")
    
    return None
    
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
