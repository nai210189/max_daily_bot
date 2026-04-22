import os
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

# ===== ТОКЕН БОТА =====
BOT_TOKEN: Final[str | None] = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Установите переменную окружения BOT_TOKEN")

# ===== ЧАСОВОЙ ПОЯС =====
MY_TIMEZONE = ZoneInfo("Asia/Krasnoyarsk")

# ===== ФАЙЛЫ =====
MESSAGES_FILE: Final[Path] = Path("messages.txt")
CHAT_ID_FILE: Final[Path] = Path("chat_id.txt")
KEYWORDS_FILE: Final[Path] = Path("keywords.json")

# ===== ВРЕМЯ ОТПРАВКИ =====
from datetime import datetime
now = datetime.now()
SEND_HOUR = now.hour
SEND_MINUTE = now.minute + 5  # через 2 минуты
if SEND_MINUTE >= 60:
    SEND_MINUTE -= 60
    SEND_HOUR += 1
