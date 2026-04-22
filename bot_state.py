class BotState:
    """Хранит состояние бота (текущий chat_id)"""
    __slots__ = ('chat_id',)
    
    def __init__(self):
        self.chat_id: int | None = None


# Глобальный экземпляр состояния
state = BotState()