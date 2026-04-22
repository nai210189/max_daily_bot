"""
Модуль для работы с PostgreSQL
"""
import asyncpg
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Глобальный пул соединений
_pool: Optional[asyncpg.Pool] = None


async def init_db(dsn: str) -> None:
    """
    Инициализирует подключение к PostgreSQL и создаёт таблицы.
    dsn: postgresql://user:password@host:5432/database
    """
    global _pool
    try:
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        logger.info("✅ Подключение к PostgreSQL установлено")
        
        # Создаём таблицы
        async with _pool.acquire() as conn:
            # Таблица для chat_id
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT UNIQUE NOT NULL,
                    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для сообщений
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_messages (
                    id SERIAL PRIMARY KEY,
                    message_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для ключевых слов
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id SERIAL PRIMARY KEY,
                    keyword TEXT NOT NULL,
                    response_type VARCHAR(20) DEFAULT 'text',
                    response_content TEXT NOT NULL,
                    response_caption TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индекс для быстрого поиска
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword)")
            
        logger.info("✅ Таблицы созданы/проверены")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
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


# ===== РАБОТА С CHAT_ID =====
async def save_chat_id_db(chat_id: int) -> None:
    """Сохраняет chat_id в БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO bot_state (chat_id) VALUES ($1) ON CONFLICT (chat_id) DO NOTHING",
            chat_id
        )
        logger.debug(f"Сохранён chat_id: {chat_id}")


async def load_chat_id_db() -> Optional[int]:
    """Загружает chat_id из БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT chat_id FROM bot_state ORDER BY id DESC LIMIT 1")
        return row['chat_id'] if row else None


# ===== РАБОТА С СООБЩЕНИЯМИ =====
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
    """Возвращает количество сообщений"""
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


# ===== РАБОТА С КЛЮЧЕВЫМИ СЛОВАМИ =====
async def add_keyword_db(keyword: str, response_type: str, content: str, caption: str = None) -> None:
    """Добавляет ключевое слово в БД"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO keywords (keyword, response_type, response_content, response_caption)
            VALUES ($1, $2, $3, $4)
        """, keyword.lower(), response_type, content, caption)
        logger.info(f"Добавлено ключевое слово: {keyword}")


async def load_keywords_db() -> List[Dict[str, Any]]:
    """
    Загружает ключевые слова из БД и группирует по ответам.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT keyword, response_type, response_content, response_caption
            FROM keywords
            ORDER BY id
        """)
        
        # Группируем по ответу
        responses_dict = {}
        for row in rows:
            key = (row['response_type'], row['response_content'], row['response_caption'])
            if key not in responses_dict:
                responses_dict[key] = {
                    "keywords": [],
                    "type": row['response_type'],
                    "content": row['response_content'],
                    "caption": row['response_caption'] or ""
                }
            responses_dict[key]["keywords"].append(row['keyword'].lower())
        
        return list(responses_dict.values())


async def clear_keywords_db() -> None:
    """Очищает таблицу ключевых слов"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE keywords")
        logger.info("Таблица ключевых слов очищена")


async def get_keywords_count_db() -> int:
    """Возвращает количество ключевых слов"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as count FROM keywords")
        return row['count'] if row else 0


# ===== МИГРАЦИЯ ИЗ ФАЙЛОВ =====
async def migrate_from_files_to_db() -> None:
    """
    Переносит данные из текстовых файлов в PostgreSQL.
    Запускается один раз при переходе на БД.
    """
    from pathlib import Path
    from config import MESSAGES_FILE, KEYWORDS_FILE, CHAT_ID_FILE
    
    logger.info("🚀 Начинаем миграцию данных из файлов в БД...")
    
    # Миграция chat_id
    if CHAT_ID_FILE.exists():
        try:
            chat_id = int(CHAT_ID_FILE.read_text(encoding='utf-8').strip())
            await save_chat_id_db(chat_id)
            logger.info(f"✅ Перенесён chat_id: {chat_id}")
        except Exception as e:
            logger.warning(f"Не удалось перенести chat_id: {e}")
    
    # Миграция сообщений
    if MESSAGES_FILE.exists():
        content = MESSAGES_FILE.read_text(encoding='utf-8')
        messages = [line.strip() for line in content.splitlines() if line.strip()]
        for msg in messages:
            await add_message_db(msg)
        logger.info(f"✅ Перенесено {len(messages)} сообщений")
    
    # Миграция ключевых слов
    if KEYWORDS_FILE.exists():
        import json
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            responses = data.get("responses", [])
            for response in responses:
                keywords = response.get("keywords", [])
                resp_type = response.get("type", "text")
                content = response.get("content", "")
                caption = response.get("caption", "")
                for keyword in keywords:
                    await add_keyword_db(keyword, resp_type, content, caption)
            logger.info(f"✅ Перенесено {len(responses)} наборов ключевых слов")
    
    logger.info("🎉 Миграция завершена!")
