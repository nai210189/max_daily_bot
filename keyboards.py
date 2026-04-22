"""
Модуль с клавиатурами для бота (maxapi 1.0.0)
"""
from typing import Dict, Any


def get_main_reply_keyboard() -> Dict[str, Any]:
    """
    Возвращает главную reply-клавиатуру (быстрое меню)
    """
    return {
        "keyboard": [
            ["📊 Статистика", "📋 Список сообщений"],
            ["➕ Добавить", "🧪 Тест"],
            ["⏰ Время", "🔄 Перезагрузить"],
            ["❌ Закрыть меню"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "input_field_placeholder": "Выберите действие..."
    }


def get_simple_reply_keyboard() -> Dict[str, Any]:
    """
    Упрощённая клавиатура (для подтверждений)
    """
    return {
        "keyboard": [
            ["✅ Да", "❌ Нет"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
        "input_field_placeholder": "Подтвердите действие..."
    }


def get_remove_keyboard() -> Dict[str, Any]:
    """
    Убирает reply-клавиатуру
    """
    return {"remove_keyboard": True}


# Словарь для обработки нажатий на кнопки
REPLY_BUTTONS_ACTIONS: Dict[str, str] = {
    "📊 Статистика": "/stats",
    "📋 Список сообщений": "/list",
    "➕ Добавить": "action_add",
    "🧪 Тест": "/test",
    "⏰ Время": "/time",
    "🔄 Перезагрузить": "/reload",
    "❌ Закрыть меню": "action_close",
    "✅ Да": "action_confirm_yes",
    "❌ Нет": "action_confirm_no",
}


def get_action_for_button(button_text: str) -> str | None:
    """Возвращает действие для нажатой кнопки"""
    return REPLY_BUTTONS_ACTIONS.get(button_text)
