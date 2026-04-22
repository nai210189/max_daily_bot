import os
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

# ===== ТОКЕН БОТА =====
BOT_TOKEN: Final[str | None] = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Установите переменную окружения BOT_TOKEN")

# ===== ПОДКЛЮЧЕНИЕ К POSTGRESQL =====
# Формат: postgresql://пользователь:пароль@хост:порт/база_данных
# Для локальной разработки: postgresql://postgres:password@localhost:5432/max_bot
# На хостинге переменная окружения DATABASE_URL должна быть установлена
DATABASE_URL: Final[str | None] = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден! Установите переменную окружения DATABASE_URL")

# ===== ЧАСОВОЙ ПОЯС =====
MY_TIMEZONE = ZoneInfo("Asia/Krasnoyarsk")

# ===== ФАЙЛЫ =====
MESSAGES_FILE: Final[Path] = Path("messages.txt")
CHAT_ID_FILE: Final[Path] = Path("chat_id.txt")
KEYWORDS_FILE: Final[Path] = Path("keywords.json")

# ===== ВРЕМЯ ОТПРАВКИ =====
SEND_HOUR = 12
SEND_MINUTE = 30
