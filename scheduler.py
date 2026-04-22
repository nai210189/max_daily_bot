import asyncio
import logging
import random
from datetime import datetime, timedelta

from config import MY_TIMEZONE, SEND_HOUR, SEND_MINUTE
from bot_state import state
from utils import load_messages

logger = logging.getLogger(__name__)


def get_next_run_time() -> datetime:
    """Возвращает следующее время отправки"""
    now = datetime.now(MY_TIMEZONE)
    target = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


async def send_daily_message(bot) -> None:
    """Отправляет случайное сообщение"""
    if state.chat_id is None:
        logger.warning("Чат не установлен")
        return
    
    try:
        messages = load_messages()
        daily_text = random.choice(messages)
        await bot.send_message(chat_id=state.chat_id, text=daily_text)
        logger.info(f"Сообщение отправлено в чат {state.chat_id}")
    except Exception as e:
        if 'chat.denied' in str(e):
            logger.warning(f"Чат {state.chat_id} недоступен")
            state.chat_id = None
        else:
            logger.error(f"Ошибка отправки: {e}")


async def daily_scheduler(bot) -> None:
    """Планировщик отправки"""
    while True:
        target = get_next_run_time()
        now_utc = datetime.now()
        wait_seconds = (target.astimezone() - now_utc).total_seconds()
        
        if wait_seconds > 0:
            hours = int(wait_seconds // 3600)
            minutes = int((wait_seconds % 3600) // 60)
            logger.info(f"Следующая отправка через {hours}ч {minutes}мин")
            
            try:
                await asyncio.sleep(wait_seconds)
            except asyncio.CancelledError:
                break
        
        await send_daily_message(bot)
