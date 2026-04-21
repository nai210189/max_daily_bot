import aiohttp
import asyncio
import logging
import random
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final
from maxapi.types import BotStarted
from zoneinfo import ZoneInfo

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, Command

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN: Final[str | None] = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Установите переменную окружения BOT_TOKEN")

MY_TIMEZONE = ZoneInfo("Asia/Krasnoyarsk")
MESSAGES_FILE: Final[Path] = Path("messages.txt")
CHAT_ID_FILE: Final[Path] = Path("chat_id.txt")
SEND_HOUR = 9
SEND_MINUTE = 0
KEYWORDS_FILE: Final[Path] = Path("keywords.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== РАБОТА С КЛЮЧЕВЫМИ СЛОВАМИ (JSON) =====
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


def load_keywords_from_json() -> list[dict[str, any]]:
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


# Кэш для ключевых слов (чтобы не читать файл при каждом сообщении)
_keywords_cache: list[dict[str, any]] | None = None


def get_keywords_config() -> list[dict[str, any]]:
    """Возвращает конфигурацию ключевых слов с кэшированием"""
    global _keywords_cache
    if _keywords_cache is None:
        _keywords_cache = load_keywords_from_json()
        logger.info(f"Загружено {len(_keywords_cache)} наборов ключевых слов")
    return _keywords_cache


def reload_keywords_config() -> list[dict[str, any]]:
    """Принудительно перезагружает конфигурацию из файла"""
    global _keywords_cache
    _keywords_cache = load_keywords_from_json()
    logger.info(f"Ключевые слова перезагружены. Загружено {len(_keywords_cache)} наборов")
    return _keywords_cache

class BotState:
    __slots__ = ('chat_id',)
    def __init__(self):
        self.chat_id: int | None = None

state = BotState()


# ===== РАБОТА С БАЗОЙ СООБЩЕНИЙ =====
def _create_example_messages() -> None:
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
    if not MESSAGES_FILE.exists():
        _create_example_messages()
    
    content = MESSAGES_FILE.read_text(encoding='utf-8')
    messages = [line.strip() for line in content.splitlines() if line.strip()]
    
    if not messages:
        raise ValueError(f"Файл {MESSAGES_FILE} пуст! Добавьте хотя бы одно сообщение.")
    
    return messages


def get_random_message(messages: list[str]) -> str:
    return random.choice(messages)


# ===== РАБОТА С CHAT_ID =====
def save_chat_id(chat_id: int) -> None:
    CHAT_ID_FILE.write_text(str(chat_id), encoding='utf-8')


def load_saved_chat_id() -> int | None:
    if CHAT_ID_FILE.exists():
        try:
            return int(CHAT_ID_FILE.read_text(encoding='utf-8').strip())
        except (ValueError, OSError):
            logger.warning("Не удалось прочитать сохранённый chat_id")
    return None


# ===== ПЛАНИРОВЩИК =====
def get_next_run_time() -> datetime:
    """Возвращает следующее время отправки (9:00 по вашему часовому поясу)"""
    now = datetime.now(MY_TIMEZONE)
    target = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


async def send_daily_message() -> None:
    if state.chat_id is None:
        logger.warning("Чат не установлен. Бот никому не отправит сообщение.")
        return
    
    try:
        messages = load_messages()
        daily_text = get_random_message(messages)
        
        await bot.send_message(chat_id=state.chat_id, text=daily_text)
        logger.info(f"Сообщение отправлено в чат {state.chat_id}: {daily_text[:50]}...")
    except Exception as e:
        logger.error(f"Ошибка при отправке: {e}", exc_info=True)

async def send_keyword_response(event: MessageCreated, response: dict[str, any]) -> None:
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
            # Проверяем, является ли content URL или локальным путём
            if content.startswith(('http://', 'https://')):
                # Отправка картинки по URL [citation:1][citation:8]
                await event.message.answer_photo(
                    photo=content,
                    caption=caption
                )
                logger.info(f"Отправлена картинка по URL: {content}")
            else:
                # Отправка локальной картинки с диска [citation:5][citation:6]
                image_path = Path(content)
                if not image_path.exists():
                    logger.warning(f"Файл картинки не найден: {image_path}")
                    await event.message.answer(caption or "❌ Изображение временно недоступно")
                    return
                
                # Отправляем файл
                with open(image_path, 'rb') as img_file:
                    await event.message.answer_photo(
                        photo=img_file,
                        caption=caption
                    )
                logger.info(f"Отправлена локальная картинка: {image_path}")
        else:
            # Если тип неизвестен, отправляем как текст
            await event.message.answer(content)
            logger.warning(f"Неизвестный тип ответа '{response_type}'")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа: {e}")
        # Отправляем fallback-сообщение
        await event.message.answer(caption or content or "❌ Произошла ошибка при отправке ответа")

async def daily_scheduler() -> None:
    while True:
        target = get_next_run_time()
        now_utc = datetime.now()
        wait_seconds = (target.astimezone() - now_utc).total_seconds()
        
        wait_delta = timedelta(seconds=wait_seconds)
        hours = wait_delta.seconds // 3600
        minutes = (wait_delta.seconds % 3600) // 60
        
        logger.info(f"Следующая отправка через {hours}ч {minutes}мин (в {target.strftime('%H:%M %d.%m.%Y')} по местному времени)")
        
        try:
            await asyncio.sleep(wait_seconds)
        except asyncio.CancelledError:
            logger.info("Планировщик остановлен")
            break
        
        await send_daily_message()


# ===== ОБРАБОТЧИКИ КОМАНД =====
async def _ensure_chat_id(event: MessageCreated) -> None:
    chat_id = event.message.chat_id  # ✅ ПРАВИЛЬНО
    if state.chat_id != chat_id:
        state.chat_id = chat_id
        save_chat_id(state.chat_id)

@dp.bot_started()
async def on_bot_started(event: BotStarted):
    """Срабатывает, когда пользователь нажимает 'Начать' в диалоге с ботом"""
    chat_id = event.chat_id  # В BotStarted chat_id доступен напрямую
    state.chat_id = chat_id
    save_chat_id(chat_id)
    await event.bot.send_message(
        chat_id=chat_id,
        text="✅ Бот активирован! Теперь каждый день в 9:00 я буду присылать сообщение."
    )
    logger.info(f"Бот активирован через BotStarted в чате {chat_id}")

@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    await _ensure_chat_id(event)
    
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
        "Я также отвечаю на слова: привет, пока, спасибо, как дела, помощь и другие!\n"
        "Добавить новые можно в файле keywords.json"
    )
    logger.info(f"Бот активирован в чате {state.chat_id}")


@dp.message_created(Command('test'))
async def cmd_test(event: MessageCreated):
    try:
        messages = load_messages()
        test_text = get_random_message(messages)
        await event.message.answer(f"🧪 Тест:\n\n{test_text}")
        # ✅ Здесь тоже используем event.message.chat_id
        logger.debug(f"Тест отправлен в чат {event.message.chat_id}")
    except Exception as e:
        await event.message.answer(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка в /test: {e}")


@dp.message_created(Command('add'))
async def cmd_add(event: MessageCreated):
    # ✅ текст сообщения - в event.message.text
    text = getattr(event.message, 'text', '') or ''
    
    # Разбираем команду: "/add текст сообщения"
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
        
        # Получаем количество ключевых слов
        keywords_config = get_keywords_config()
        keywords_count = len(keywords_config)
        
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
    """Показывает текущее время в вашем часовом поясе"""
    now = datetime.now(MY_TIMEZONE)
    await event.message.answer(f"🕐 {now.strftime('%H:%M:%S %d.%m.%Y')} (по вашему времени)")


@dp.message_created()
async def handle_keywords(event: MessageCreated):
    """
    Отвечает на сообщения по ключевым словам из JSON файла.
    Этот обработчик срабатывает для любых сообщений (кроме команд).
    """
    # Получаем текст сообщения
    text = getattr(event.message, 'text', '') or ''
    text_lower = text.lower().strip()
    
    # Игнорируем команды (начинаются с /)
    if text_lower.startswith('/'):
        return
    
    # Игнорируем слишком длинные сообщения (вряд ли это ключевое слово)
    if len(text_lower) > 100:
        return
    
    # Загружаем конфигурацию
    responses = get_keywords_config()
    
    # Ищем подходящий ответ
    for response in responses:
        keywords = response.get("keywords", [])
        
        # Приводим ключевые слова к нижнему регистру для сравнения
        keywords_lower = [kw.lower() for kw in keywords]
        
        # Проверяем, есть ли хотя бы одно ключевое слово в сообщении
        for keyword in keywords_lower:
            if keyword in text_lower:
                logger.info(f"Сработало ключевое слово '{keyword}' в чате {event.message.chat_id}")
                await send_keyword_response(event, response)
                return

@dp.message_created()
async def handle_unknown(event: MessageCreated):
    text = getattr(event.message, 'text', '') or ''
    if text and text.startswith('/') and text not in ['/start', '/test', '/add', '/list', '/stats', '/time']:
        await event.message.answer("❓ Неизвестная команда. Напишите /start для списка команд.")

@dp.message_created(Command('reload'))
async def cmd_reload(event: MessageCreated):
    """Перезагружает ключевые слова из JSON файла"""
    # Проверяем, что команду дал владелец бота
    if state.chat_id is not None and event.message.chat_id != state.chat_id:
        await event.message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        reload_keywords_config()
        await event.message.answer("✅ Ключевые слова успешно перезагружены из keywords.json!")
    except Exception as e:
        await event.message.answer(f"❌ Ошибка при перезагрузке: {e}")


# ===== ЗАПУСК =====
async def main() -> None:
    logger.info("🚀 Запуск ежедневного бота...")
    
    saved_id = load_saved_chat_id()
    if saved_id:
        state.chat_id = saved_id
        logger.info(f"Восстановлен chat_id: {state.chat_id}")
    
    scheduler_task = asyncio.create_task(daily_scheduler())
    
    await bot.delete_webhook()
    
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await asyncio.gather(scheduler_task, return_exceptions=True)
        logger.info("Бот остановлен")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
