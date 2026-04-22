import asyncpg
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Пул соединений с БД (глобальный)
_pool: Optional[asyncpg.Pool] = None


async def init_db(dsn: str) -> None:
    """
    Инициализирует подключение к PostgreSQL и создаёт таблицы.
    dsn: postgresql://user:password@host:5432/database
    """
    global _pool
    try:
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        logger.info("Подключение к PostgreSQL установлено")
        
        # Создаём таблицы, если их нет
        async with _pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT UNIQUE NOT NULL,
                    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_messages (
                    id SERIAL PRIMARY KEY,
                    message_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""""
                CREATE TABLE IF NOT EXISTS keywords (
                    id SERIAL PRIMARY KEY,
                    keyword TEXT NOT NULL,
                    response_type VARCHAR(20) DEFAULT 'text',
                    response_content TEXT NOT NULL,
                    response_caption TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword)")
            
            # Создаём триггер для автоматического обновления updated_at
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """)
            
        logger.info("Таблицы созданы/проверены")
    except Exception as e:
        logger.error(f"Ошибка подключения к PostgreSQL: {e}")
        raise


async def close_db() -> None:
    """Закрывает пул соединений"""
    global _pool
    if _pool:
        await _pool.close()
        logger.info("Соединение с PostgreSQL закрыто")


def get_pool() -> asyncpg.Pool:
    """Возвращает пул соединений"""
    if _pool is None:
        raise RuntimeError("База данных не инициализирована")
    return _pool


# ===== РАБОТА С BOT_STATE =====
async def save_chat_id_db(chat_id: int) -> None:
    """Сохраняет chat_id в БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO bot_state (chat_id) VALUES ($1) ON CONFLICT (chat_id) DO NOTHING",
            chat_id
        )
        logger.info(f"Сохранён chat_id: {chat_id}")


async def load_chat_id_db() -> Optional[int]:
    """Загружает chat_id из БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT chat_id FROM bot_state ORDER BY id DESC LIMIT 1")
        return row['chat_id'] if row else None


# ===== РАБОТА С DAILY_MESSAGES =====
async def add_message_db(text: str) -> None:
    """Добавляет сообщение в БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO daily_messages (message_text) VALUES ($1)",
            text
        )
        logger.info(f"Добавлено сообщение: {text[:50]}...")


async def load_messages_db() -> List[str]:
    """Загружает все сообщения из БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT message_text FROM daily_messages ORDER BY id")
        return [row['message_text'] for row in rows]


async def clear_messages_db() -> None:
    """Очищает таблицу сообщений"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE daily_messages")
        logger.info("База сообщений очищена")


async def get_random_message_db() -> Optional[str]:
    """Возвращает случайное сообщение из БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT message_text FROM daily_messages ORDER BY RANDOM() LIMIT 1")
        return row['message_text'] if row else None


async def get_messages_count_db() -> int:
    """Возвращает количество сообщений в БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as count FROM daily_messages")
        return row['count'] if row else 0


async def get_messages_total_length_db() -> int:
    """Возвращает суммарную длину всех сообщений"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT SUM(LENGTH(message_text)) as total FROM daily_messages")
        return row['total'] or 0


# ===== РАБОТА С KEYWORDS =====
async def load_keywords_db() -> List[Dict[str, Any]]:
    """
    Загружает ключевые слова и ответы из БД.
    Группирует несколько ключевых слов в один ответ.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT keyword, response_type, response_content, response_caption, description
            FROM keywords
            ORDER BY id
        """)
        
        # Группируем по ответу (если несколько ключевых слов ведут к одному ответу)
        responses_dict = {}
        for row in rows:
            # Используем response_content как ключ для группировки
            key = (row['response_type'], row['response_content'], row['response_caption'])
            if key not in responses_dict:
                responses_dict[key] = {
                    "keywords": [],
                    "type": row['response_type'],
                    "content": row['response_content'],
                    "caption": row['response_caption'] or "",
                    "description": row['description'] or ""
                }
            responses_dict[key]["keywords"].append(row['keyword'].lower())
        
        return list(responses_dict.values())


async def add_keyword_db(keyword: str, response_type: str, content: str, caption: str = None) -> None:
    """Добавляет новое ключевое слово в БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO keywords (keyword, response_type, response_content, response_caption)
            VALUES ($1, $2, $3, $4)
        """, keyword.lower(), response_type, content, caption)
        logger.info(f"Добавлено ключевое слово: {keyword}")


async def delete_keyword_db(keyword: str) -> None:
    """Удаляет ключевое слово из БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM keywords WHERE keyword = $1", keyword.lower())
        logger.info(f"Удалено ключевое слово: {keyword}")


async def get_keywords_count_db() -> int:
    """Возвращает количество ключевых слов в БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as count FROM keywords")
        return row['count'] if row else 0
