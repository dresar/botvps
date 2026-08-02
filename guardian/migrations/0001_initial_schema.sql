-- =====================================================================
-- SERVERINKA GUARDIAN — Initial Database Schema
-- Migration: 0001
-- Semua 8 tabel beserta indeks
-- =====================================================================

-- ---- Tabel users ----
CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER     PRIMARY KEY AUTOINCREMENT,
    telegram_id         INTEGER     NOT NULL UNIQUE,
    username            TEXT        DEFAULT NULL,
    full_name           TEXT        NOT NULL DEFAULT 'Unknown',
    role                TEXT        NOT NULL DEFAULT 'viewer'
                                    CHECK(role IN ('super_admin', 'admin', 'operator', 'viewer')),
    is_active           INTEGER     NOT NULL DEFAULT 1
                                    CHECK(is_active IN (0, 1)),
    is_blocked          INTEGER     NOT NULL DEFAULT 0
                                    CHECK(is_blocked IN (0, 1)),
    alert_enabled       INTEGER     NOT NULL DEFAULT 1
                                    CHECK(alert_enabled IN (0, 1)),
    language_code       TEXT        NOT NULL DEFAULT 'id',
    notes               TEXT        DEFAULT NULL,
    added_by            INTEGER     DEFAULT NULL REFERENCES users(id),
    created_at          TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at          TEXT        NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- ---- Tabel sessions ----
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state           TEXT        NOT NULL DEFAULT 'idle',
    state_data      TEXT        DEFAULT NULL,
    created_at      TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    last_active_at  TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    expires_at      TEXT        DEFAULT NULL
);

-- ---- Tabel audit_logs ----
CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER     DEFAULT NULL REFERENCES users(id) ON DELETE SET NULL,
    telegram_id     INTEGER     DEFAULT NULL,
    action          TEXT        NOT NULL,
    target          TEXT        DEFAULT NULL,
    parameters      TEXT        DEFAULT NULL,
    result_status   TEXT        NOT NULL DEFAULT 'pending'
                                CHECK(result_status IN ('pending', 'success', 'failed', 'denied')),
    error_message   TEXT        DEFAULT NULL,
    duration_ms     INTEGER     DEFAULT NULL,
    created_at      TEXT        NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- ---- Tabel scheduled_jobs ----
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id                  INTEGER     PRIMARY KEY AUTOINCREMENT,
    name                TEXT        NOT NULL,
    description         TEXT        DEFAULT NULL,
    job_type            TEXT        NOT NULL
                                    CHECK(job_type IN ('cron', 'interval', 'one_time')),
    cron_expression     TEXT        DEFAULT NULL,
    interval_seconds    INTEGER     DEFAULT NULL,
    run_at              TEXT        DEFAULT NULL,
    action              TEXT        NOT NULL,
    parameters          TEXT        DEFAULT NULL,
    is_active           INTEGER     NOT NULL DEFAULT 1
                                    CHECK(is_active IN (0, 1)),
    created_by          INTEGER     DEFAULT NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at          TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at          TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    last_run_at         TEXT        DEFAULT NULL,
    next_run_at         TEXT        DEFAULT NULL,
    run_count           INTEGER     NOT NULL DEFAULT 0,
    failure_count       INTEGER     NOT NULL DEFAULT 0
);

-- ---- Tabel job_run_logs ----
CREATE TABLE IF NOT EXISTS job_run_logs (
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER     NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
    started_at      TEXT        NOT NULL,
    finished_at     TEXT        DEFAULT NULL,
    status          TEXT        NOT NULL DEFAULT 'running'
                                CHECK(status IN ('running', 'success', 'failed')),
    output          TEXT        DEFAULT NULL,
    error_message   TEXT        DEFAULT NULL
);

-- ---- Tabel alert_configs ----
CREATE TABLE IF NOT EXISTS alert_configs (
    id                  INTEGER     PRIMARY KEY AUTOINCREMENT,
    metric_name         TEXT        NOT NULL
                                    CHECK(metric_name IN (
                                        'cpu_percent', 'ram_percent', 'disk_percent',
                                        'swap_percent', 'load_average_1m',
                                        'network_bytes_recv', 'network_bytes_sent'
                                    )),
    threshold_value     REAL        NOT NULL,
    threshold_unit      TEXT        NOT NULL DEFAULT 'percent'
                                    CHECK(threshold_unit IN ('percent', 'bytes', 'count', 'seconds')),
    comparison_op       TEXT        NOT NULL DEFAULT 'gt'
                                    CHECK(comparison_op IN ('gt', 'gte', 'lt', 'lte', 'eq')),
    cooldown_minutes    INTEGER     NOT NULL DEFAULT 30,
    is_active           INTEGER     NOT NULL DEFAULT 1
                                    CHECK(is_active IN (0, 1)),
    created_by          INTEGER     DEFAULT NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at          TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at          TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    last_triggered_at   TEXT        DEFAULT NULL,
    trigger_count       INTEGER     NOT NULL DEFAULT 0
);

-- ---- Tabel plugin_configs ----
CREATE TABLE IF NOT EXISTS plugin_configs (
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,
    plugin_name     TEXT        NOT NULL,
    config_key      TEXT        NOT NULL,
    config_value    TEXT        NOT NULL,
    value_type      TEXT        NOT NULL DEFAULT 'string'
                                CHECK(value_type IN ('string', 'integer', 'float', 'boolean', 'json')),
    description     TEXT        DEFAULT NULL,
    created_at      TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at      TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    UNIQUE(plugin_name, config_key)
);

-- ---- Tabel migrations ----
CREATE TABLE IF NOT EXISTS migrations (
    id          INTEGER     PRIMARY KEY AUTOINCREMENT,
    version     INTEGER     NOT NULL UNIQUE,
    name        TEXT        NOT NULL,
    applied_at  TEXT        NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- =====================================================================
-- INDEKS
-- =====================================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id
    ON users(telegram_id);

CREATE INDEX IF NOT EXISTS idx_users_role_active
    ON users(role, is_active);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id
    ON sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
    ON sessions(expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id_created_at
    ON audit_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action
    ON audit_logs(action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_result_status
    ON audit_logs(result_status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_active
    ON scheduled_jobs(is_active, next_run_at);

CREATE INDEX IF NOT EXISTS idx_job_run_logs_job_id
    ON job_run_logs(job_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_alert_configs_active
    ON alert_configs(is_active, metric_name);

CREATE INDEX IF NOT EXISTS idx_plugin_configs_plugin_name
    ON plugin_configs(plugin_name);

CREATE UNIQUE INDEX IF NOT EXISTS idx_migrations_version
    ON migrations(version);

-- =====================================================================
-- DEFAULT ALERT CONFIGS
-- =====================================================================

INSERT OR IGNORE INTO alert_configs
    (metric_name, threshold_value, threshold_unit, comparison_op, cooldown_minutes)
VALUES
    ('cpu_percent',     90.0, 'percent', 'gt', 30),
    ('ram_percent',     90.0, 'percent', 'gt', 30),
    ('disk_percent',    90.0, 'percent', 'gt', 60),
    ('swap_percent',    80.0, 'percent', 'gt', 60),
    ('load_average_1m', 8.0,  'count',   'gt', 15);
