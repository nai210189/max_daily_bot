import logging
from datetime import datetime, timedelta
import pytz

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, Command, BotStarted

from config import TIMEZONE
from db import (
    save_chat_id, get_chat_id,
    add_daily_message, get_all_daily_messages, get_random_daily_message,
    get_daily_messages_count, clear_daily_messages,
    add_reminder, get_user_reminders, delete_reminder
)
from utils import (
    get_chat_id_from_event, get_user_id_from_event, get_text_from_event,
    parse_datetime, format_reminder_list
)

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher, bot: Bot):
    
    @dp.bot_started()
    async def on_bot_started(event: BotStarted):
        """Пользователь нажал 'Начать'"""
        chat_id = event.chat_id
        await save_chat_id(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован!\n\n"
                 "📋 **Команды:**\n"
                 "/start - активировать бота\n"
                 "/menu - показать меню\n"
                 "/daily_add <текст> - добавить сообщение в ежедневную рассылку\n"
                 "/daily_list - список ежедневных сообщений\n"
                 "/daily_clear - очистить все сообщения\n"
                 "/remind <время> <текст> - создать напоминание\n"
                 "/remind_list - список напоминаний\n"
                 "/remind_del <id> - удалить напоминание\n"
                 "/test - отправить тестовое сообщение\n\n"
                 "📅 **Формат времени:**\n"
                 "• `15:30` - сегодня в 15:30\n"
                 "• `2024-12-31 15:30` - конкретная дата\n"
                 "• `+1h` - через час\n"
                 "• `+30m` - через 30 минут\n"
                 "• `+2d` - через 2 дня"
        )
        logger.info(f"Бот активирован в чате {chat_id}")

    @dp.message_created(Command('start'))
    async def cmd_start(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        if not chat_id:
            return
        await save_chat_id(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Бот активирован!\n\nОтправьте /menu для списка команд"
        )

    @dp.message_created(Command('menu'))
    async def cmd_menu(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        if not chat_id:
            return
        await bot.send_message(
            chat_id=chat_id,
            text="📋 **Доступные команды:**\n\n"
                 "**Ежедневные сообщения:**\n"
                 "• `/daily_add <текст>` - добавить сообщение\n"
                 "• `/daily_list` - список сообщений\n"
                 "• `/daily_clear` - очистить все\n\n"
                 "**Напоминания:**\n"
                 "• `/remind <время> <текст>` - создать\n"
                 "• `/remind_list` - список\n"
                 "• `/remind_del <id>` - удалить\n\n"
                 "**Другое:**\n"
                 "• `/test` - тестовое сообщение\n"
                 "• `/menu` - это меню",
            parse_mode="markdown"
        )

    # ===== ЕЖЕДНЕВНЫЕ СООБЩЕНИЯ =====
    
    @dp.message_created(Command('daily_add'))
    async def cmd_daily_add(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        text = get_text_from_event(event)
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2 or not parts[1].strip():
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Использование: `/daily_add <текст сообщения>`",
                parse_mode="markdown"
            )
            return
        
        await add_daily_message(parts[1].strip())
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Сообщение добавлено в ежедневную рассылку!"
        )

    @dp.message_created(Command('daily_list'))
    async def cmd_daily_list(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        messages = await get_all_daily_messages()
        
        if not messages:
            await bot.send_message(chat_id=chat_id, text="📭 Нет сообщений в ежедневной рассылке")
            return
        
        lines = [f"{i+1}. {msg[:60]}..." if len(msg) > 60 else f"{i+1}. {msg}" 
                 for i, msg in enumerate(messages)]
        text = f"📋 **Ежедневные сообщения ({len(messages)}):**\n\n" + "\n".join(lines)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="markdown")

    @dp.message_created(Command('daily_clear'))
    async def cmd_daily_clear(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        await clear_daily_messages()
        await bot.send_message(chat_id=chat_id, text="✅ Все сообщения удалены!")

    # ===== НАПОМИНАНИЯ =====
    
    @dp.message_created(Command('remind'))
    async def cmd_remind(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        user_id = get_user_id_from_event(event)
        text = get_text_from_event(event)
        parts = text.split(maxsplit=2)
        
        if len(parts) < 3 or not parts[1].strip() or not parts[2].strip():
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Использование: `/remind <время> <текст напоминания>`\n\n"
                     "Примеры:\n"
                     "• `/remind 15:30 Позвонить клиенту`\n"
                     "• `/remind 2024-12-31 15:30 Купить подарки`\n"
                     "• `/remind +1h Встреча через час`\n"
                     "• `/remind +30m Сделать перерыв`",
                parse_mode="markdown"
            )
            return
        
        time_str = parts[1].strip()
        reminder_text = parts[2].strip()
        
        remind_at = parse_datetime(time_str, TIMEZONE)
        if not remind_at:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Неверный формат времени: `{time_str}`\n\n"
                     "Поддерживаемые форматы:\n"
                     "• `15:30` - сегодня в 15:30\n"
                     "• `2024-12-31 15:30` - конкретная дата\n"
                     "• `+1h` - через час\n"
                     "• `+30m` - через 30 минут\n"
                     "• `+2d` - через 2 дня",
                parse_mode="markdown"
            )
            return
        
        await add_reminder(chat_id, user_id, reminder_text, remind_at)
        
        tz = pytz.timezone(TIMEZONE)
        time_str_formatted = remind_at.astimezone(tz).strftime("%d.%m.%Y в %H:%M")
        
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Напоминание создано!\n\n"
                 f"📅 **Когда:** {time_str_formatted}\n"
                 f"📝 **Текст:** {reminder_text}"
        )

    @dp.message_created(Command('remind_list'))
    async def cmd_remind_list(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        reminders = await get_user_reminders(chat_id)
        text = format_reminder_list(reminders)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="markdown")

    @dp.message_created(Command('remind_del'))
    async def cmd_remind_del(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        text = get_text_from_event(event)
        parts = text.split()
        
        if len(parts) < 2 or not parts[1].isdigit():
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Использование: `/remind_del <id>`\n\n"
                     "ID напоминания можно увидеть в `/remind_list`",
                parse_mode="markdown"
            )
            return
        
        reminder_id = int(parts[1])
        success = await delete_reminder(reminder_id, chat_id)
        
        if success:
            await bot.send_message(chat_id=chat_id, text=f"✅ Напоминание #{reminder_id} удалено!")
        else:
            await bot.send_message(chat_id=chat_id, text=f"❌ Напоминание #{reminder_id} не найдено")

    # ===== ТЕСТ =====
    
    @dp.message_created(Command('test'))
    async def cmd_test(event: MessageCreated):
        chat_id = get_chat_id_from_event(event)
        message = await get_random_daily_message()
        if message:
            await bot.send_message(chat_id=chat_id, text=f"🧪 Тестовое сообщение:\n\n{message}")
        else:
            await bot.send_message(chat_id=chat_id, text="📭 Нет сообщений в базе. Добавьте через /daily_add")

    # ===== КЛЮЧЕВЫЕ СЛОВА =====
    
    @dp.message_created()
    async def handle_keywords(event: MessageCreated):
        text = get_text_from_event(event)
        text_lower = text.lower().strip()
        
        if text_lower.startswith('/') or len(text_lower) > 100:
            return
        
        keywords_responses = {
            "привет": "👋 Здравствуйте! Чем могу помочь?",
            "здравствуй": "👋 Здравствуйте! Чем могу помочь?",
            "пока": "До свидания! Хорошего дня! 👋",
            "спасибо": "Пожалуйста! Всегда рад помочь! 👍",
            "как дела": "Всё отлично! А у вас? 😊",
            "помощь": "📋 Напишите /menu для списка команд",
            "бот": "Я бот для напоминаний и рассылок! 🤖",
        }
        
        for keyword, response in keywords_responses.items():
            if keyword in text_lower:
                chat_id = get_chat_id_from_event(event)
                await bot.send_message(chat_id=chat_id, text=response)
                return

    # ===== НЕИЗВЕСТНЫЕ КОМАНДЫ =====
    
    @dp.message_created()
    async def handle_unknown(event: MessageCreated):
        text = get_text_from_event(event)
        known_commands = [
            '/start', '/menu', '/test',
            '/daily_add', '/daily_list', '/daily_clear',
            '/remind', '/remind_list', '/remind_del'
        ]
        if text and text.startswith('/') and text not in known_commands:
            chat_id = get_chat_id_from_event(event)
            await bot.send_message(
                chat_id=chat_id,
                text="❓ Неизвестная команда. Напишите /menu для списка команд."
            )