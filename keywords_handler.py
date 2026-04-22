import logging
from typing import Any

from maxapi.types import MessageCreated
from utils import load_keywords, get_chat_id_from_event
from db import get_pool

logger = logging.getLogger(__name__)


# Кэш для ключевых слов (опционально, для производительности)
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
    """Отправляет ответ пользователю (текст или картинку)"""
    response_type = response.get("type", "text")
    content = response.get("content", "")
    caption = response.get("caption", "")
    chat_id = get_chat_id_from_event(event)
    
    try:
        if response_type == "text":
            await bot.send_message(chat_id=chat_id, text=content)
            logger.debug(f"Отправлен текстовый ответ: {content[:50]}...")
        elif response_type == "image":
            if content.startswith(('http://', 'https://')):
                await bot.send_photo(chat_id=chat_id, photo=content, caption=caption)
                logger.info(f"Отправлена картинка по URL: {content}")
            else:
                logger.warning(f"Локальные картинки не поддерживаются: {content}")
                await bot.send_message(chat_id=chat_id, text=caption or "❌ Изображение временно недоступно")
        else:
            await bot.send_message(chat_id=chat_id, text=content)
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа: {e}")
