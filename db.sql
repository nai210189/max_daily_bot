-- Таблица для хранения ID чата
CREATE TABLE bot_state (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для ежедневных сообщений
CREATE TABLE daily_messages (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для напоминаний
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT,
    text TEXT NOT NULL,
    remind_at TIMESTAMP NOT NULL,        -- Когда отправить
    repeat_type VARCHAR(20) DEFAULT 'once', -- once, daily, weekly, monthly
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX idx_reminders_remind_at ON reminders(remind_at) WHERE is_active = TRUE;
CREATE INDEX idx_reminders_chat_id ON reminders(chat_id);