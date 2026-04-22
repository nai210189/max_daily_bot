import asyncio
import logging
from datetime import datetime, timedelta

from config import MY_TIMEZONE, SEND_HOUR, SEND_MINUTE
from bot_state import state
from utils import load_messages
from maxapi import Bot

logger = logging.getLogger(__name__)


def get_next_run_time() -> datetime:
    """Возвращает следующее время отправки"""
    now = datetime.now(MY_TIMEZONE)
    target = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


async def send_daily_message(bot: Bot) -> None:
    """Отправляет случайное сообщение в нужный чат"""
    if state.chat_id is None:
        logger.warning("Чат не установлен. Бот никому не отправит сообщение.")
        return
    
    try:
        messages = load_messages()
        daily_text = random.choice(messages)  # import random нужен вверху
        
        await bot.send_message(chat_id=state.chat_id, text=daily_text)
        logger.info(f"Сообщение отправлено в чат {state.chat_id}: {daily_text[:50]}...")
    except Exception as e:
        if 'chat.denied' in str(e) or 'dialog.suspended' in str(e):
            logger.warning(f"Чат {state.chat_id} недоступен. Очищаем chat_id.")
            state.chat_id = None
        else:
            logger.error(f"Ошибка при отправке: {e}", exc_info=True)


async def daily_scheduler(bot: Bot) -> None:
    """Планировщик отправки сообщений"""
    import random  # локальный импорт для избежания циклических зависимостей
    
    while True:
        target = get_next_run_time()
        now_utc = datetime.now()
        wait_seconds = (target.astimezone() - now_utc).total_seconds()
        
        wait_delta = timedelta(seconds=wait_seconds)
        hours = wait_delta.seconds // 3600
        minutes = (wait_delta.seconds % 3600) // 60
        
        logger.info(f"Следующая отправка через {hours}ч {minutes}мин (в {target.strftime('%H:%M %d.%m.%Y')})")
        
        try:
            await asyncio.sleep(wait_seconds)
        except asyncio.CancelledError:
            logger.info("Планировщик остановлен")
            break
        
        await send_daily_message(bot)