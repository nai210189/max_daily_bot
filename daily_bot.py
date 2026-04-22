import asyncio
import logging

from maxapi import Bot, Dispatcher

from config import BOT_TOKEN
from bot_state import state
from utils import load_saved_chat_id
from scheduler import daily_scheduler
from message_handler import register_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Создаём бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main() -> None:
    """Главная функция запуска"""
    logger.info("🚀 Запуск ежедневного бота...")
    
    # Регистрируем обработчики (передаём и dp, и bot)
    register_handlers(dp, bot)  # 👈 ИСПРАВЛЕНО: передаём оба аргумента
    
    # Восстанавливаем сохранённый chat_id
    saved_id = load_saved_chat_id()
    if saved_id:
        state.chat_id = saved_id
        logger.info(f"Восстановлен chat_id: {state.chat_id}")
    
    # Запускаем планировщик
    scheduler_task = asyncio.create_task(daily_scheduler(bot))
    
    # Очищаем вебхуки и запускаем polling
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
