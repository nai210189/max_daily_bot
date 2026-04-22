import json
import logging
from pathlib import Path
from typing import Any

from maxapi.types import MessageCreated
from config import KEYWORDS_FILE
from utils import get_chat_id_from_event

logger = logging.getLogger(__name__)


def create_example_keywords_file() -> None:
    """Создаёт пример файла keywords.json"""
    example_config = {
        "responses": [
            {
                "keywords": ["привет", "здравствуй", "добрый день"],
                "type": "text",
                "content": "👋 Здравствуйте! Чем могу помочь?"
            },
            {
                "keywords": ["пока", "до свидания", "всего хорошего"],
                "type": "text",
                "content": "До свидания! Хорошего дня! 👋"
            },
            {
                "keywords": ["спасибо", "благодарю", "спс"],
                "type": "text",
                "content": "Пожалуйста! Всегда рад помочь! 👍"
            },
            {
                "keywords": ["как дела", "как жизнь", "как ты"],
                "type": "text",
                "content": "Всё отлично! А у вас? 😊"
            },
            {
                "keywords": ["помощь", "команды", "help", "что умеешь"],
                "type": "text",
                "content": "📋 Напишите /start для списка всех команд"
            },
            {
                "keywords": ["бот", "ты бот", "кто ты"],
                "type": "text",
                "content": "Я бот для ежедневной рассылки полезных сообщений! 🤖"
            }
        ]
    }
    with open(KEYWORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, ensure_ascii=False, indent=4)
    logger.info(f"Создан пример файла {KEYWORDS_FILE}")


def load_keywords_from_json() -> list[dict[str, Any]]:
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


def get_keywords_config() -> list[dict[str, Any]]:
    """Возвращает конфигурацию с кэшированием"""
    global _keywords_cache
    if _keywords_cache is None:
        _keywords_cache = load_keywords_from_json()
        logger.info(f"Загружено {len(_keywords_cache)} наборов ключевых слов")
    return _keywords_cache


def reload_keywords_config() -> list[dict[str, Any]]:
    """Перезагружает конфигурацию"""
    global _keywords_cache
    _keywords_cache = load_keywords_from_json()
    logger.info(f"Перезагружено {len(_keywords_cache)} наборов")
    return _keywords_cache


async def send_keyword_response(event: MessageCreated, response: dict[str, Any], bot) -> None:
    """Отправляет ответ пользователю (только текст, без картинок)"""
    response_type = response.get("type", "text")
    content = response.get("content", "")
    caption = response.get("caption", "")
    chat_id = get_chat_id_from_event(event)
    
    try:
        if response_type == "text":
            await bot.send_message(chat_id=chat_id, text=content)
            logger.debug(f"Отправлен текстовый ответ: {content[:50]}...")
        else:
            # Для image и других типов просто отправляем текст или подпись
            if caption:
                await bot.send_message(chat_id=chat_id, text=caption)
            else:
                await bot.send_message(chat_id=chat_id, text=content or "❌ Ответ не может быть отправлен")
            logger.warning(f"Тип ответа '{response_type}' преобразован в текст")
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа: {e}")
        await bot.send_message(chat_id=chat_id, text="❌ Произошла ошибка при отправке ответа")
