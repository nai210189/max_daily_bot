import asyncio
import logging
from datetime import datetime, timedelta

from config import MY_TIMEZONE, SEND_HOUR, SEND_MINUTE
from bot_state import state
from db import get_random_message_db

logger = logging.getLogger(__name__)


def get_next_run_time() -> datetime:
    """Возвращает следующее время отправки"""
    now = datetime.now(MY_TIMEZONE)
    target = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


async def send_daily_message(bot) -> None:
    """Отправляет случайное сообщение из БД"""
    if state.chat_id is None:
        logger.warning("Чат не установлен. Бот никому не отправит сообщение.")
        return
    
    try:
        daily_text = await get_random_message_db()
        if not daily_text:
            logger.warning("Нет сообщений в базе данных")
            await bot.send_message(
                chat_id=state.chat_id,
                text="⚠️ База сообщений пуста! Добавьте сообщения через /add"
            )
            return
        
        await bot.send_message(chat_id=state.chat_id, text=daily_text)
        logger.info(f"Сообщение отправлено в чат {state.chat_id}: {daily_text[:50]}...")
    except Exception as e:
        if 'chat.denied' in str(e) or 'dialog.suspended' in str(e):
            logger.warning(f"Чат {state.chat_id} недоступен. Очищаем chat_id.")
            state.chat_id = None
        else:
            logger.error(f"Ошибка при отправке: {e}", exc_info=True)


async def daily_scheduler(bot) -> None:
    """Планировщик отправки сообщений"""
    while True:
        target = get_next_run_time()
        now_utc = datetime.now()
        wait_seconds = (target.astimezone() - now_utc).total_seconds()
        
        if wait_seconds > 0:
            hours = int(wait_seconds // 3600)
            minutes = int((wait_seconds % 3600) // 60)
            logger.info(f"Следующая отправка через {hours}ч {minutes}мин (в {target.strftime('%H:%M %d.%m.%Y')})")
            
            try:
                await asyncio.sleep(wait_seconds)
            except asyncio.CancelledError:
                logger.info("Планировщик остановлен")
                break
        
        await send_daily_message(bot)
