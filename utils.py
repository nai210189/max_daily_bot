import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


def get_chat_id_from_event(event) -> int | None:
    """Извлекает chat_id из события"""
    if hasattr(event, 'chat_id'):
        return event.chat_id
    if hasattr(event, 'message') and hasattr(event.message, 'recipient'):
        if hasattr(event.message.recipient, 'chat_id'):
            return event.message.recipient.chat_id
    return None


def get_user_id_from_event(event) -> int | None:
    """Извлекает user_id из события"""
    if hasattr(event, 'user_id'):
        return event.user_id
    if hasattr(event, 'message') and hasattr(event.message, 'sender'):
        if hasattr(event.message.sender, 'user_id'):
            return event.message.sender.user_id
    return None


def get_text_from_event(event) -> str:
    """Извлекает текст сообщения"""
    if hasattr(event, 'message') and hasattr(event.message, 'body'):
        if hasattr(event.message.body, 'text'):
            return event.message.body.text
    return ""


def parse_datetime(time_str: str, tz_str: str) -> datetime | None:
    """
    Парсит дату и время из строки.
    Форматы: 
    - "2024-12-31 15:30"
    - "15:30" (сегодня)
    - "+1h" (через час)
    - "+30m" (через 30 минут)
    """
    tz = pytz.timezone(tz_str)
    now = datetime.now(tz)
    
    time_str = time_str.strip().lower()
    
    # Формат: "2024-12-31 15:30"
    if len(time_str) == 16 and time_str[4] == '-' and time_str[7] == '-':
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            return tz.localize(dt)
        except ValueError:
            pass
    
    # Формат: "15:30" (сегодня)
    if ':' in time_str and len(time_str) <= 5:
        try:
            hour, minute = map(int, time_str.split(':'))
            dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if dt <= now:
                dt += timedelta(days=1)
            return dt
        except ValueError:
            pass
    
    # Формат: "+1h", "+30m", "+2d"
    if time_str.startswith('+'):
        import re
        match = re.match(r'\+(\d+)([hdm])', time_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if unit == 'h':
                dt = now + timedelta(hours=value)
            elif unit == 'd':
                dt = now + timedelta(days=value)
            elif unit == 'm':
                dt = now + timedelta(minutes=value)
            else:
                return None
            return dt
    
    return None


def format_reminder_list(reminders: list) -> str:
    """Форматирует список напоминаний для вывода"""
    if not reminders:
        return "📭 У вас нет активных напоминаний"
    
    lines = ["📋 **Ваши напоминания:**\n"]
    for r in reminders:
        dt = r['remind_at'].strftime("%d.%m.%Y %H:%M")
        repeat_icon = {
            'once': '🔘',
            'daily': '🔄',
            'weekly': '📅',
            'monthly': '📆'
        }.get(r['repeat_type'], '🔘')
        lines.append(f"{repeat_icon} #{r['id']} | {dt}\n   {r['text'][:50]}")
    
    return "\n".join(lines)