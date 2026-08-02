-- =====================================================================
-- MIGRATION 0006: AI CRON SCHEDULER ENGINE & EXPANDED ALERT LOGS
-- =====================================================================

-- Tabel SQLite untuk Penjadwalan AI & User Reminders
CREATE TABLE IF NOT EXISTS ai_scheduled_tasks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id      INTEGER NOT NULL,
    task_type        TEXT    NOT NULL DEFAULT 'interval', -- 'cron', 'interval', 'one_shot'
    cron_expression  TEXT,   -- e.g. '0 8 * * *'
    interval_seconds INTEGER,-- e.g. 600
    run_at           TEXT,   -- ISO timestamp untuk one_shot
    message          TEXT    NOT NULL,
    is_active        INTEGER NOT NULL DEFAULT 1,
    last_run_at      TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_ai_scheduled_tasks_active ON ai_scheduled_tasks(is_active);
