import logging
from maxapi.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

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


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для подтверждения действий
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no")
            ]
        ]
    )
    return keyboard


def get_action_keyboard() -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для выбора действий
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить сообщение", callback_data="action_add"),
                InlineKeyboardButton(text="📋 Показать список", callback_data="action_list")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="action_stats"),
                InlineKeyboardButton(text="🕐 Время", callback_data="action_time")
            ],
            [
                InlineKeyboardButton(text="🔄 Перезагрузить", callback_data="action_reload"),
                InlineKeyboardButton(text="🧪 Тест", callback_data="action_test")
            ]
        ]
    )
    return keyboard
