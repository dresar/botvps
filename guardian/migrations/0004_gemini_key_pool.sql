-- =====================================================================
-- MIGRATION 0004: GEMINI API KEY POOL FOR LOCAL SQLITE STORAGE
-- =====================================================================

CREATE TABLE IF NOT EXISTS gemini_api_keys (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key      TEXT    UNIQUE NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 1,
    usage_count  INTEGER NOT NULL DEFAULT 0,
    error_count  INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT,
    last_used_at TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_gemini_api_keys_active ON gemini_api_keys(is_active, last_used_at);
