-- =====================================================================
-- MIGRATION 0003: AI HERMES-STYLE MEMORY SYSTEM
-- =====================================================================

-- Tabel memori jangka panjang (Long-Term Memory & User Rules)
CREATE TABLE IF NOT EXISTS ai_memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    memory_type TEXT    NOT NULL DEFAULT 'rule', -- 'rule', 'preference', 'fact'
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_ai_memories_user ON ai_memories(telegram_id);

-- Tabel histori percakapan (Short-Term Conversation Context)
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    role        TEXT    NOT NULL, -- 'user', 'assistant'
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_history_user ON ai_chat_history(telegram_id);
