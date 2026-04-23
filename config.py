import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден!")

# Подключение к БД
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден!")

# Настройки
TIMEZONE = os.getenv("TIMEZONE", "Asia/Krasnoyarsk")
SEND_HOUR = int(os.getenv("SEND_HOUR", 9))
SEND_MINUTE = int(os.getenv("SEND_MINUTE", 0))