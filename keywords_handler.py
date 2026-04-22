import json
import logging
from pathlib import Path
from typing import Any

from maxapi.types import MessageCreated
from config import KEYWORDS_FILE
from utils import get_chat_id_from_event, load_keywords

logger = logging.getLogger(__name__)

# Кэш для ключевых слов
_keywords_cache: list[dict[str, Any]] | None = None


async def load_keywords_from_json() -> list[dict[str, Any]]:
    """Загружает конфигурацию ключевых слов"""
    if not KEYWORDS_FILE.exists():
        create_example_keywords_file()
    
    try:
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("responses", [])
    except Exception as e:
        logger.error(f"Ошибка загрузки {KEYWORDS_FILE}: {e}")
        return []


_keywords_cache: list[dict[str, Any]] | None = None


async def get_keywords_config() -> list[dict[str, Any]]:
    """Возвращает конфигурацию ключевых слов с кэшированием"""
    global _keywords_cache
    if _keywords_cache is None:
        _keywords_cache = await load_keywords()
        logger.info(f"Загружено {len(_keywords_cache)} наборов ключевых слов из БД")
    return _keywords_cache


async def reload_keywords_config() -> list[dict[str, Any]]:
    """Принудительно перезагружает конфигурацию из БД"""
    global _keywords_cache
    _keywords_cache = await load_keywords()
    logger.info(f"Ключевые слова перезагружены. Загружено {len(_keywords_cache)} наборов")
    return _keywords_cache


async def send_keyword_response(event: MessageCreated, response: dict[str, Any], bot) -> None:
    """Отправляет ответ пользователю (только текст)"""
    response_type = response.get("type", "text")
    content = response.get("content", "")
    caption = response.get("caption", "")
    chat_id = get_chat_id_from_event(event)
    
    try:
        if response_type == "text":
            await bot.send_message(chat_id=chat_id, text=content)
            logger.debug(f"Отправлен текстовый ответ: {content[:50]}...")
        else:
            text_to_send = caption if caption else content
            if text_to_send:
                await bot.send_message(chat_id=chat_id, text=text_to_send)
            else:
                await bot.send_message(chat_id=chat_id, text="✅ Сообщение получено")
            logger.warning(f"Тип ответа '{response_type}' преобразован в текст")
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа: {e}")
        try:
            await bot.send_message(chat_id=chat_id, text="❌ Произошла ошибка при отправке ответа")
        except:
            pass
