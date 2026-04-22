import logging
from maxapi.types import ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger(__name__)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главная клавиатура с основными командами
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Тест"),
                KeyboardButton(text="➕ Добавить"),
            ],
            [
                KeyboardButton(text="📋 Список"),
                KeyboardButton(text="📊 Статистика"),
            ],
            [
                KeyboardButton(text="🕐 Время"),
                KeyboardButton(text="🔄 Перезагрузить"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура для отмены операции
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
