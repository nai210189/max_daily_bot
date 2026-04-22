"""
Модуль с клавиатурами для бота
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_main_reply_keyboard() -> Dict[str, Any]:
    """
    Возвращает главную reply-клавиатуру (быстрое меню).
    Кнопки отправляются как обычные сообщения.
    """
    keyboard = {
        "keyboard": [
            ["📊 Статистика", "📋 Список сообщений"],
            ["➕ Добавить", "🧪 Тест"],
            ["⏰ Время", "🔄 Перезагрузить"],
            ["❌ Закрыть меню"]
        ],
        "resize_keyboard": True,           # Автоматически подгонять размер
        "one_time_keyboard": False,        # Не скрывать после нажатия
        "input_field_placeholder": "Выберите действие..."  # Подсказка
    }
    return keyboard


def get_simple_reply_keyboard() -> Dict[str, Any]:
    """
    Упрощённая клавиатура (для быстрых ответов)
    """
    keyboard = {
        "keyboard": [
            ["✅ Да", "❌ Нет"],
            ["🔙 Назад"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,         # Скрыть после одного нажатия
        "input_field_placeholder": "Подтвердите действие..."
    }
    return keyboard


def get_admin_reply_keyboard() -> Dict[str, Any]:
    """
    Расширенная клавиатура для администратора (с дополнительными функциями)
    """
    keyboard = {
        "keyboard": [
            ["📊 Статистика", "📋 Список сообщений", "➕ Добавить"],
            ["🧪 Тест", "⏰ Время", "🔄 Перезагрузить"],
            ["📅 Следующая отправка", "🗑 Очистить базу", "❌ Закрыть меню"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "input_field_placeholder": "Панель администратора"
    }
    return keyboard


def get_remove_keyboard() -> Dict[str, Any]:
    """
    Убирает reply-клавиатуру (скрывает кнопки)
    """
    return {"remove_keyboard": True}


# Словарь для обработки нажатий на кнопки
# Сопоставляет текст кнопки с командой или действием
REPLY_BUTTONS_ACTIONS = {
    "📊 Статистика": "/stats",
    "📋 Список сообщений": "/list",
    "➕ Добавить": "action_add",
    "🧪 Тест": "/test",
    "⏰ Время": "/time",
    "🔄 Перезагрузить": "/reload",
    "📅 Следующая отправка": "/next",
    "🗑 Очистить базу": "action_clear",
    "❌ Закрыть меню": "action_close",
    "✅ Да": "action_confirm_yes",
    "❌ Нет": "action_confirm_no",
    "🔙 Назад": "/menu"
}


def get_action_for_button(button_text: str) -> Optional[str]:
    """
    Возвращает действие для нажатой кнопки
    """
    return REPLY_BUTTONS_ACTIONS.get(button_text)
