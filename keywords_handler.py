import json
import logging
from pathlib import Path
from typing import Any

from maxapi.types import MessageCreated
from config import KEYWORDS_FILE

logger = logging.getLogger(__name__)


def create_example_keywords_file() -> None:
    """Создаёт пример файла keywords.json, если его нет"""
    example_config = {
        "responses": [
            {
                "keywords": ["привет", "здравствуй", "добрый день"],
                "type": "text",
                "content": "👋 Здравствуйте! Чем могу помочь?",
                "description": "Приветствие"
            },
            {
                "keywords": ["пока", "до свидания", "всего хорошего"],
                "type": "text",
                "content": "До свидания! Хорошего дня! 👋",
                "description": "Прощание"
            },
            {
                "keywords": ["спасибо", "благодарю", "спс"],
                "type": "text",
                "content": "Пожалуйста! Всегда рад помочь! 👍",
                "description": "Благодарность"
            },
            {
                "keywords": ["как дела", "как жизнь", "как ты"],
                "type": "text",
                "content": "Всё отлично! А у вас? 😊",
                "description": "Вопрос о делах"
            },
            {
                "keywords": ["помощь", "команды", "help", "что умеешь"],
                "type": "text",
                "content": "📋 Напишите /start для списка всех команд",
                "description": "Справка"
            },
            {
                "keywords": ["бот", "ты бот", "кто ты"],
                "type": "text",
                "content": "Я бот для ежедневной рассылки полезных сообщений! 🤖",
                "description": "Представление бота"
            }
        ]
    }
    with open(KEYWORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, ensure_ascii=False, indent=4)
    logger.info(f"Создан пример файла {KEYWORDS_FILE}")


def load_keywords_from_json() -> list[dict[str, Any]]:
    """Загружает конфигурацию ключевых слов из JSON файла"""
    if not KEYWORDS_FILE.exists():
        create_example_keywords_file()
    
    try:
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("responses", [])
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга {KEYWORDS_FILE}: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки {KEYWORDS_FILE}: {e}")
        return []


# Кэш для ключевых слов
_keywords_cache: list[dict[str, Any]] | None = None


def get_keywords_config() -> list[dict[str, Any]]:
    """Возвращает конфигурацию ключевых слов с кэшированием"""
    global _keywords_cache
    if _keywords_cache is None:
        _keywords_cache = load_keywords_from_json()
        logger.info(f"Загружено {len(_keywords_cache)} наборов ключевых слов")
    return _keywords_cache


def reload_keywords_config() -> list[dict[str, Any]]:
    """Принудительно перезагружает конфигурацию из файла"""
    global _keywords_cache
    _keywords_cache = load_keywords_from_json()
    logger.info(f"Ключевые слова перезагружены. Загружено {len(_keywords_cache)} наборов")
    return _keywords_cache


async def send_keyword_response(event: MessageCreated, response: dict[str, Any]) -> None:
    """
    Отправляет ответ пользователю (текст или картинку).
    """
    response_type = response.get("type", "text")
    content = response.get("content", "")
    caption = response.get("caption", "")
    
    try:
        if response_type == "text":
            await event.message.answer(content)
            logger.debug(f"Отправлен текстовый ответ: {content[:50]}...")
            
        elif response_type == "image":
            if content.startswith(('http://', 'https://')):
                await event.message.answer_photo(photo=content, caption=caption)
                logger.info(f"Отправлена картинка по URL: {content}")
            else:
                image_path = Path(content)
                if not image_path.exists():
                    logger.warning(f"Файл картинки не найден: {image_path}")
                    await event.message.answer(caption or "❌ Изображение временно недоступно")
                    return
                with open(image_path, 'rb') as img_file:
                    await event.message.answer_photo(photo=img_file, caption=caption)
                logger.info(f"Отправлена локальная картинка: {image_path}")
        else:
            await event.message.answer(content)
            logger.warning(f"Неизвестный тип ответа '{response_type}'")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа: {e}")
        await event.message.answer(caption or content or "❌ Произошла ошибка при отправке ответа")
