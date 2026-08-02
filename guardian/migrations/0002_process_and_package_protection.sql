-- =====================================================================
-- MIGRATION 0002: AUTO PROCESS GUARDIAN & PACKAGE PROTECTION TABLES
-- =====================================================================

-- Tabel riwayat tindakan kill CPU
CREATE TABLE IF NOT EXISTS cpu_kill_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pid          INTEGER NOT NULL,
    process_name TEXT    NOT NULL,
    username     TEXT    NOT NULL,
    cpu_percent  REAL    NOT NULL,
    memory_percent REAL  NOT NULL,
    cmdline      TEXT    NOT NULL,
    running_time TEXT    NOT NULL,
    action_taken TEXT    NOT NULL, -- 'SIGTERM', 'SIGKILL', 'WARNING'
    status       TEXT    NOT NULL, -- 'success', 'failed'
    reason       TEXT    NOT NULL,
    executed_at  TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_cpu_kill_history_pid ON cpu_kill_history(pid);
CREATE INDEX IF NOT EXISTS idx_cpu_kill_history_process ON cpu_kill_history(process_name);
CREATE INDEX IF NOT EXISTS idx_cpu_kill_history_executed ON cpu_kill_history(executed_at);

-- Tabel aturan whitelist & blacklist CPU guard
CREATE TABLE IF NOT EXISTS cpu_guard_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type  TEXT    NOT NULL, -- 'whitelist', 'blacklist'
    value      TEXT    NOT NULL UNIQUE,
    added_by   INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- Tabel log tindakan package protection / uninstall
CREATE TABLE IF NOT EXISTS package_guard_logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name      TEXT    NOT NULL,
    install_method    TEXT    NOT NULL, -- 'binary', 'systemd', 'npm', 'pip', 'apt', 'snap'
    binary_location   TEXT    NOT NULL,
    config_location   TEXT    NOT NULL,
    cache_location    TEXT    NOT NULL,
    status            TEXT    NOT NULL, -- 'success', 'failed'
    details           TEXT    NOT NULL,
    executed_at       TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_package_guard_logs_pkg ON package_guard_logs(package_name);

-- Tabel daftar paket terlarang (blocked packages)
CREATE TABLE IF NOT EXISTS blocked_packages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    added_by   INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- Inisialisasi default blocked package: opencode
INSERT OR IGNORE INTO blocked_packages (name, added_by) VALUES ('opencode', 7896674035);
