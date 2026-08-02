-- Migration 0007: Terminal Plugin — Shell Access Sessions & History
-- ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS terminal_sessions (
    user_id     INTEGER PRIMARY KEY,
    cwd         TEXT    NOT NULL DEFAULT '/',
    last_active REAL    NOT NULL DEFAULT (unixepoch('now'))
);

CREATE TABLE IF NOT EXISTS terminal_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    command     TEXT    NOT NULL,
    exit_code   INTEGER NOT NULL DEFAULT 0,
    executed_at REAL    NOT NULL DEFAULT (unixepoch('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_terminal_history_user_id ON terminal_history(user_id);
