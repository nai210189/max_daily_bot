import asyncio
import logging
import random
from datetime import datetime, time
from pathlib import Path

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "f9LHodD0cOKO2Y8nxlqx67FOkppCR2lTMkH3d5erq-TRgY08VyEkLY-aqiI79difaBQowe8fxq9yOzhhNtOp"  # Токен от Master Bot
MESSAGES_FILE = "messages.txt"  # Файл с сообщениями
CHAT_ID = None  # ID чата, куда отправлять. Если None - бот будет ждать команду /start

# Создаём бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ===== РАБОТА С БАЗОЙ СООБЩЕНИЙ =====
def load_messages() -> list[str]:
    """Загружает сообщения из текстового файла, по одному на строку"""
    if not Path(MESSAGES_FILE).exists():
        # Если файла нет - создаём с примерами
        example_messages = [
            "Доброе утро! Хорошего дня! ☀️",
            "Не забывайте пить воду 💧",
            "Сегодня отличный день для новых свершений! 🚀",
            "Улыбнитесь, это бесплатно 😊",
            "Среда — маленькая пятница! 🎉"
        ]
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(example_messages))
        logger.info(f"Создан файл {MESSAGES_FILE} с примерами сообщений")
    
    with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
        messages = [line.strip() for line in f if line.strip()]
    
    if not messages:
        raise ValueError(f"Файл {MESSAGES_FILE} пуст! Добавьте хотя бы одно сообщение.")
    
    return messages


def get_random_message(messages: list[str]) -> str:
    """Возвращает случайное сообщение из списка"""
    return random.choice(messages)


# ===== ОТПРАВКА ЕЖЕДНЕВНОГО СООБЩЕНИЯ =====
async def send_daily_message():
    """Отправляет случайное сообщение в нужный чат"""
    global CHAT_ID
    
    if CHAT_ID is None:
        logger.warning("Чат не установлен. Бот никому не отправит сообщение.")
        return
    
    try:
        messages = load_messages()
        daily_text = get_random_message(messages)
        
        await bot.send_message(chat_id=CHAT_ID, text=daily_text)
        logger.info(f"Ежедневное сообщение отправлено в чат {CHAT_ID}: {daily_text[:50]}...")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")


async def daily_scheduler():
    """Планировщик, который запускает отправку каждый день в 9:00"""
    while True:
        now = datetime.now()
        # Целевое время - сегодня в 9:00
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Если уже прошло 9:00 сегодня - планируем на завтра
        if now >= target:
            target = target.replace(day=now.day + 1)
        
        # Сколько секунд ждать до 9:00
        wait_seconds = (target - now).total_seconds()
        
        # Округляем до целых секунд для красоты лога
        hours = int(wait_seconds // 3600)
        minutes = int((wait_seconds % 3600) // 60)
        
        logger.info(f"Следующая отправка через {hours}ч {minutes}мин (в {target.strftime('%H:%M %d.%m.%Y')})")
        
        await asyncio.sleep(wait_seconds)
        
        # Отправляем сообщение
        await send_daily_message()


# ===== ОБРАБОТЧИКИ КОМАНД ПОЛЬЗОВАТЕЛЯ =====
@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    """При команде /start - запоминаем чат и приветствуем"""
    global CHAT_ID
    
    chat_id = event.message.chat.id
    CHAT_ID = chat_id
    
    # Сохраняем chat_id в файл, чтобы не потерять при перезапуске
    with open("chat_id.txt", "w") as f:
        f.write(str(chat_id))
    
    await event.message.answer(
        "✅ Бот активирован!\n\n"
    )


@dp.message_created(Command('test'))
async def cmd_test(event: MessageCreated):
    """Отправляет случайное сообщение сразу (для теста)"""
    try:
        messages = load_messages()
        test_text = get_random_message(messages)
        await event.message.answer(f"🧪 Тестовое сообщение:\n\n{test_text}")
        logger.info(f"Тестовое сообщение отправлено пользователю {event.message.chat.id}")
    except Exception as e:
        await event.message.answer(f"❌ Ошибка: {e}")


@dp.message_created(Command('add'))
async def cmd_add(event: MessageCreated):
    """Добавляет новое сообщение в базу"""
    # Получаем текст после команды /add
    message_text = event.message.body.get('text', '')
    parts = message_text.split(maxsplit=1)
    
    if len(parts) < 2:
        await event.message.answer("❌ Использование: /add <текст сообщения>")
        return
    
    new_message = parts[1].strip()
    
    # Добавляем в файл
    with open(MESSAGES_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n{new_message}")
    
    await event.message.answer(f"✅ Сообщение добавлено:\n\n{new_message}")


@dp.message_created(Command('list'))
async def cmd_list(event: MessageCreated):
    """Показывает все сообщения из базы"""
    try:
        messages = load_messages()
        
        if not messages:
            await event.message.answer("📭 База сообщений пуста.")
            return
        
        # Формируем красивое сообщение со списком
        list_text = "📋 **Список сообщений в базе:**\n\n"
        for i, msg in enumerate(messages, 1):
            # Обрезаем слишком длинные сообщения для списка
            display_msg = msg[:50] + "..." if len(msg) > 50 else msg
            list_text += f"{i}. {display_msg}\n"
        
        # Если сообщение слишком длинное для одного ответа
        if len(list_text) > 4000:
            # Отправляем файлом
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                await event.message.answer_document(
                    document=f,
                    caption="📄 Полный список сообщений"
                )
        else:
            await event.message.answer(list_text)
            
    except Exception as e:
        await event.message.answer(f"❌ Ошибка: {e}")


@dp.message_created(Command('stats'))
async def cmd_stats(event: MessageCreated):
    """Показывает статистику базы сообщений"""
    try:
        messages = load_messages()
        total = len(messages)
        
        # Считаем среднюю длину сообщения
        avg_len = sum(len(msg) for msg in messages) // total if total > 0 else 0
        
        stats_text = (
            f"📊 **Статистика базы сообщений**\n\n"
            f"• Всего сообщений: {total}\n"
            f"• Средняя длина: {avg_len} символов\n"
            f"• Файл: {MESSAGES_FILE}\n"
            f"• Время отправки: 9:00 ежедневно"
        )
        
        await event.message.answer(stats_text)
        
    except Exception as e:
        await event.message.answer(f"❌ Ошибка: {e}")


# ===== ЗАПУСК БОТА =====
async def main():
    global CHAT_ID
    
    logger.info("Запуск ежедневного бота...")
    
    # Пытаемся восстановить сохранённый chat_id
    if Path("chat_id.txt").exists():
        with open("chat_id.txt", "r") as f:
            try:
                CHAT_ID = int(f.read().strip())
                logger.info(f"Восстановлен chat_id: {CHAT_ID}")
            except:
                pass
    
    # Запускаем планировщик в фоновом режиме
    asyncio.create_task(daily_scheduler())
    
    # Запускаем обработку команд
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
