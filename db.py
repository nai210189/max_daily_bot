import asyncpg
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import DATABASE_URL

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Инициализация базы данных"""
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    
    async with _pool.acquire() as conn:
        # bot_state
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # daily_messages
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_messages (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # reminders
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT,
                text TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                repeat_type VARCHAR(20) DEFAULT 'once',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Индексы
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminders_remind_at 
            ON reminders(remind_at) WHERE is_active = TRUE
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminders_chat_id 
            ON reminders(chat_id)
        """)
        
        # Пример сообщения для старта
        await conn.execute("""
            INSERT INTO daily_messages (text) 
            SELECT 'Доброе утро! Хорошего дня! ☀️' 
            WHERE NOT EXISTS (SELECT 1 FROM daily_messages)
        """)
    
    logger.info("✅ База данных инициализирована")


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        logger.info("Соединение с БД закрыто")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("База данных не инициализирована")
    return _pool


# ===== BOT STATE =====
async def save_chat_id(chat_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO bot_state (chat_id) VALUES ($1) ON CONFLICT (chat_id) DO NOTHING",
            chat_id
        )
        logger.info(f"Сохранён chat_id: {chat_id}")


async def get_chat_id() -> Optional[int]:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT chat_id FROM bot_state ORDER BY id DESC LIMIT 1")
        return row["chat_id"] if row else None


# ===== DAILY MESSAGES =====
async def add_daily_message(text: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO daily_messages (text) VALUES ($1)", text)
        logger.info(f"Добавлено сообщение: {text[:50]}...")


async def get_all_daily_messages() -> List[str]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT text FROM daily_messages ORDER BY id")
        return [row["text"] for row in rows]


async def get_random_daily_message() -> Optional[str]:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT text FROM daily_messages ORDER BY RANDOM() LIMIT 1")
        return row["text"] if row else None


async def get_daily_messages_count() -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as count FROM daily_messages")
        return row["count"] if row else 0


async def clear_daily_messages():
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE daily_messages")
        logger.info("Все сообщения удалены")


# ===== REMINDERS =====
async def add_reminder(chat_id: int, user_id: int, text: str, remind_at: datetime, repeat_type: str = "once"):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO reminders (chat_id, user_id, text, remind_at, repeat_type)
            VALUES ($1, $2, $3, $4, $5)
        """, chat_id, user_id, text, remind_at, repeat_type)
        logger.info(f"Добавлено напоминание для чата {chat_id}: {text[:50]}...")


async def get_due_reminders() -> List[Dict[str, Any]]:
    """Возвращает напоминания, которые пора отправить"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, chat_id, user_id, text, remind_at, repeat_type
            FROM reminders
            WHERE is_active = TRUE AND remind_at <= NOW()
            ORDER BY remind_at
        """)
        return [dict(row) for row in rows]


async def mark_reminder_completed(reminder_id: int):
    """Отмечает напоминание как выполненное"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE reminders SET is_active = FALSE WHERE id = $1", reminder_id)


async def update_reminder_for_repeat(reminder_id: int, remind_at: datetime):
    """Обновляет время повторяющегося напоминания"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE reminders 
            SET remind_at = $1, is_active = TRUE 
            WHERE id = $2
        """, remind_at, reminder_id)


async def get_user_reminders(chat_id: int) -> List[Dict[str, Any]]:
    """Возвращает активные напоминания пользователя"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, text, remind_at, repeat_type
            FROM reminders
            WHERE chat_id = $1 AND is_active = TRUE
            ORDER BY remind_at
        """, chat_id)
        return [dict(row) for row in rows]


async def delete_reminder(reminder_id: int, chat_id: int) -> bool:
    """Удаляет напоминание (только если оно принадлежит чату)"""
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM reminders WHERE id = $1 AND chat_id = $2",
            reminder_id, chat_id
        )
        return result != "DELETE 0"