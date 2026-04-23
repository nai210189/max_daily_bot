import asyncio
import logging

from maxapi import Bot, Dispatcher

from config import BOT_TOKEN
from db import init_db, close_db, get_chat_id
from handlers import register_handlers
from scheduler import scheduler_loop

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Создаём бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main():
    logger.info("🚀 Запуск бота...")
    
    # Инициализация БД
    await init_db()
    
    # Регистрация обработчиков
    register_handlers(dp, bot)
    
    # Запуск планировщика в фоне
    scheduler_task = asyncio.create_task(scheduler_loop(bot))
    
    # Запуск бота
    await bot.delete_webhook()
    
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await asyncio.gather(scheduler_task, return_exceptions=True)
        await close_db()
        logger.info("Бот остановлен")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)