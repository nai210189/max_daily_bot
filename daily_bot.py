import logging
from typing import List, Optional

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
    add_keyword_db as add_keyword,
    delete_keyword_db as delete_keyword,
    get_keywords_count_db as get_keywords_count,
)

logger = logging.getLogger(__name__)


# ===== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ CHAT_ID =====
def get_chat_id_from_event(event) -> int | None:
    """
    Универсальное получение chat_id из события.
    """
    if hasattr(event, 'chat_id'):
        return event.chat_id
    if hasattr(event, 'message') and hasattr(event.message, 'recipient'):
        if hasattr(event.message.recipient, 'chat_id'):
            return event.message.recipient.chat_id
    logger.warning(f"Не удалось получить chat_id из {type(event)}")
    return None


# ===== МИГРАЦИЯ ДАННЫХ ИЗ ФАЙЛОВ В БД =====
async def migrate_from_files_to_db() -> None:
    """
    Переносит данные из текстовых файлов в PostgreSQL.
    Запустите один раз при переходе на БД.
    """
    from pathlib import Path
    from config import MESSAGES_FILE, KEYWORDS_FILE
    
    logger.info("Начинаем миграцию данных из файлов в БД...")
    
    # Миграция сообщений
    if MESSAGES_FILE.exists():
        content = MESSAGES_FILE.read_text(encoding='utf-8')
        messages = [line.strip() for line in content.splitlines() if line.strip()]
        for msg in messages:
            await add_message(msg)
        logger.info(f"Перенесено {len(messages)} сообщений из {MESSAGES_FILE}")
    
    # Миграция ключевых слов (если есть JSON файл)
    if KEYWORDS_FILE.exists():
        import json
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            responses = data.get("responses", [])
            for response in responses:
                keywords = response.get("keywords", [])
                resp_type = response.get("type", "text")
                content = response.get("content", "")
                caption = response.get("caption", "")
                for keyword in keywords:
                    await add_keyword(keyword, resp_type, content, caption)
            logger.info(f"Перенесено {len(responses)} наборов ключевых слов из {KEYWORDS_FILE}")
    
    logger.info("Миграция завершена!")
