-- =====================================================================
-- MIGRATION 0005: GROQ AI BACKUP POOL AND HERMES DYNAMIC SKILL ENGINE
-- =====================================================================

-- Tabel SQLite Key Pool untuk Groq AI Backup
CREATE TABLE IF NOT EXISTS groq_api_keys (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key      TEXT    UNIQUE NOT NULL,
    model        TEXT    NOT NULL DEFAULT 'llama-3.3-70b-versatile',
    is_active    INTEGER NOT NULL DEFAULT 1,
    usage_count  INTEGER NOT NULL DEFAULT 0,
    error_count  INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT,
    last_used_at TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_groq_api_keys_active ON groq_api_keys(is_active, last_used_at);

-- Tabel Hermes Dynamic Skill Engine (Skill & Capabilities)
CREATE TABLE IF NOT EXISTS ai_skills (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name    TEXT    NOT NULL,
    description   TEXT,
    trigger_words TEXT,
    instructions  TEXT    NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_ai_skills_active ON ai_skills(is_active);
