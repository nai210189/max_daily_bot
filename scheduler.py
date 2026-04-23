import asyncio
import logging
from datetime import datetime, timedelta
import pytz

from config import TIMEZONE, SEND_HOUR, SEND_MINUTE
from db import (
    get_chat_id, get_random_daily_message,
    get_due_reminders, mark_reminder_completed, update_reminder_for_repeat
)

logger = logging.getLogger(__name__)


def get_next_daily_time() -> datetime:
    """Возвращает следующее время для ежедневной рассылки"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    target = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


async def send_daily_message(bot):
    """Отправляет ежедневное сообщение"""
    chat_id = await get_chat_id()
    if not chat_id:
        logger.warning("Чат не активирован")
        return
    
    message = await get_random_daily_message()
    if message:
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Ежедневное сообщение отправлено в чат {chat_id}")
    else:
        logger.warning("Нет сообщений для ежедневной рассылки")


async def process_reminders(bot):
    """Обрабатывает напоминания, которые пора отправить"""
    reminders = await get_due_reminders()
    
    for reminder in reminders:
        try:
            # Отправляем напоминание
            tz = pytz.timezone(TIMEZONE)
            remind_time = reminder['remind_at'].astimezone(tz).strftime("%d.%m.%Y %H:%M")
            
            await bot.send_message(
                chat_id=reminder['chat_id'],
                text=f"⏰ **Напоминание!**\n\n"
                     f"📅 {remind_time}\n"
                     f"📝 {reminder['text']}"
            )
            logger.info(f"Напоминание #{reminder['id']} отправлено в чат {reminder['chat_id']}")
            
            # Обрабатываем повторение
            repeat_type = reminder['repeat_type']
            
            if repeat_type == 'once':
                await mark_reminder_completed(reminder['id'])
            
            elif repeat_type == 'daily':
                next_time = reminder['remind_at'] + timedelta(days=1)
                await update_reminder_for_repeat(reminder['id'], next_time)
                logger.info(f"Напоминание #{reminder['id']} перенесено на {next_time}")
            
            elif repeat_type == 'weekly':
                next_time = reminder['remind_at'] + timedelta(weeks=1)
                await update_reminder_for_repeat(reminder['id'], next_time)
            
            elif repeat_type == 'monthly':
                # Приблизительно: добавляем 30 дней
                next_time = reminder['remind_at'] + timedelta(days=30)
                await update_reminder_for_repeat(reminder['id'], next_time)
                
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания #{reminder['id']}: {e}")


async def scheduler_loop(bot):
    """Основной цикл планировщика"""
    logger.info("🕐 Планировщик запущен")
    
    while True:
        now = datetime.now(pytz.utc)
        
        # Проверяем напоминания каждую минуту
        await process_reminders(bot)
        
        # Проверяем, не пора ли отправить ежедневное сообщение
        target = get_next_daily_time()
        if now >= target.astimezone(pytz.utc):
            await send_daily_message(bot)
            # После отправки обновляем target на завтра
            target = get_next_daily_time()
        
        # Ждём 60 секунд до следующей проверки
        await asyncio.sleep(60)