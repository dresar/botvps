# 04 — Desain Database
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [03_TECH_STACK.md](03_TECH_STACK.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Prinsip Desain Database](#2-prinsip-desain-database)
3. [Entity Relationship Diagram](#3-entity-relationship-diagram)
4. [Skema Tabel Lengkap](#4-skema-tabel-lengkap)
5. [Indeks Database](#5-indeks-database)
6. [Strategi Migrasi](#6-strategi-migrasi)
7. [Query Patterns Umum](#7-query-patterns-umum)
8. [Konfigurasi SQLite](#8-konfigurasi-sqlite)
9. [Strategi Backup Database](#9-strategi-backup-database)
10. [Panduan Migrasi ke PostgreSQL](#10-panduan-migrasi-ke-postgresql)
11. [Keputusan Desain](#11-keputusan-desain)
12. [Checklist Implementasi](#12-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan seluruh desain database Serverinka Guardian. Mencakup seluruh tabel, relasi, indeks, tipe data, constraint, dan alasan di balik setiap keputusan desain. Database harus mampu mendukung semua fitur MVP dan dapat dimigrasi ke PostgreSQL tanpa refaktor besar.

---

## 2. Prinsip Desain Database

### Prinsip Utama

1. **Kesederhanaan:** Hanya buat tabel yang benar-benar dibutuhkan.
2. **Normalisasi:** Minimal di 3NF (Third Normal Form) untuk menghindari redudansi.
3. **Auditability:** Setiap perubahan data penting harus dapat dilacak.
4. **Portabilitas:** Tidak menggunakan tipe data atau syntax yang SQLite-only.
5. **Indeks Strategis:** Indeks hanya pada kolom yang sering di-query, tidak berlebihan.
6. **Soft Delete:** Data penting tidak dihapus secara fisik, hanya dinonaktifkan.
7. **Timestamps:** Setiap tabel memiliki `created_at` dan `updated_at`.
8. **UUID vs Integer ID:** Menggunakan INTEGER PRIMARY KEY AUTOINCREMENT untuk SQLite (performa), rencana migrasi ke UUID untuk PostgreSQL.

### Aturan Tipe Data

| Konsep | SQLite Type | PostgreSQL Type (Future) |
|--------|-------------|--------------------------|
| Identifier | INTEGER | BIGSERIAL / UUID |
| Teks pendek (<= 255 char) | TEXT | VARCHAR(255) |
| Teks panjang | TEXT | TEXT |
| Angka bulat | INTEGER | INTEGER / BIGINT |
| Angka desimal | REAL | NUMERIC |
| Boolean | INTEGER (0/1) | BOOLEAN |
| Timestamp | TEXT (ISO 8601) | TIMESTAMPTZ |
| JSON | TEXT | JSONB |
| Enum/status | TEXT | TEXT dengan CHECK constraint |

---

## 3. Entity Relationship Diagram

```
+----------------+       +-------------------+       +----------------+
|     users      |       |    audit_logs     |       |    sessions    |
+----------------+       +-------------------+       +----------------+
| id (PK)        |<------| user_id (FK)      |       | id (PK)        |
| telegram_id    |       | id (PK)           |  +--->| user_id (FK)   |
| username       |       | action            |  |    | created_at     |
| full_name      |       | target            |  |    | last_active_at |
| role           |       | parameters        |  |    | is_active      |
| is_active      |       | result_status     |  |    +----------------+
| is_admin       |       | error_message     |  |
| alert_enabled  |       | ip_address        |  |
| created_at     |       | created_at        |  |
| updated_at     |       +-------------------+  |
+----------------+                              |
        ^                                       |
        |                                       |
        +---------------------------------------+
        |
+----------------+       +-------------------+       +-------------------+
| scheduled_jobs |       |  alert_configs    |       |  plugin_configs   |
+----------------+       +-------------------+       +-------------------+
| id (PK)        |       | id (PK)           |       | id (PK)           |
| name           |       | metric_name       |       | plugin_name       |
| job_type       |       | threshold_value   |       | config_key        |
| cron_expression|       | threshold_unit    |       | config_value      |
| action         |       | comparison_op     |       | value_type        |
| parameters     |       | cooldown_minutes  |       | created_at        |
| is_active      |       | is_active         |       | updated_at        |
| created_by (FK)|------>| created_by (FK)   |       +-------------------+
| created_at     |       | created_at        |
| updated_at     |       | updated_at        |
| last_run_at    |       | last_triggered_at |
| next_run_at    |       +-------------------+
+----------------+
        |
        |
+----------------+       +-------------------+
| job_run_logs   |       |   migrations      |
+----------------+       +-------------------+
| id (PK)        |       | id (PK)           |
| job_id (FK)    |<------| version           |
| started_at     |       | name              |
| finished_at    |       | applied_at        |
| status         |       +-------------------+
| output         |
| error_message  |
+----------------+
```

---

## 4. Skema Tabel Lengkap

### 4.1 Tabel `users`

Menyimpan semua pengguna yang terdaftar di bot beserta role dan preferensi mereka.

```sql
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
```

**Deskripsi Kolom:**

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| `id` | INTEGER PK | Internal identifier |
| `telegram_id` | INTEGER UNIQUE | Telegram User ID (immutable, tidak berubah) |
| `username` | TEXT NULL | Username Telegram (bisa berubah, opsional) |
| `full_name` | TEXT | Nama lengkap dari Telegram profile |
| `role` | TEXT | Role RBAC: super_admin, admin, operator, viewer |
| `is_active` | INTEGER | 0=dinonaktifkan, 1=aktif |
| `is_blocked` | INTEGER | 0=normal, 1=diblokir sementara |
| `alert_enabled` | INTEGER | Apakah user ini menerima alert otomatis |
| `language_code` | TEXT | Kode bahasa preferensi (id, en) |
| `notes` | TEXT NULL | Catatan admin tentang user ini |
| `added_by` | INTEGER FK NULL | User yang menambahkan user ini |
| `created_at` | TEXT | Timestamp UTC saat dibuat (ISO 8601) |
| `updated_at` | TEXT | Timestamp UTC saat terakhir diupdate |

---

### 4.2 Tabel `sessions`

Menyimpan sesi aktif pengguna untuk tracking state percakapan.

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state           TEXT        NOT NULL DEFAULT 'idle',
    state_data      TEXT        DEFAULT NULL,
    created_at      TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    last_active_at  TEXT        NOT NULL DEFAULT (datetime('now', 'utc')),
    expires_at      TEXT        DEFAULT NULL
);
```

**Deskripsi Kolom:**

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| `id` | INTEGER PK | Internal identifier |
| `user_id` | INTEGER FK | Referensi ke tabel users |
| `state` | TEXT | State percakapan saat ini (idle, confirming_reboot, dll) |
| `state_data` | TEXT NULL | Data JSON untuk state (misal: service name yang akan direstart) |
| `created_at` | TEXT | Timestamp sesi dibuat |
| `last_active_at` | TEXT | Timestamp terakhir user aktif |
| `expires_at` | TEXT NULL | Kapan sesi kedaluwarsa (NULL = tidak kedaluwarsa) |

---

### 4.3 Tabel `audit_logs`

Mencatat semua tindakan yang dilakukan melalui bot. Ini adalah tabel yang paling sering ditulis.

```sql
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
```

**Deskripsi Kolom:**

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| `id` | INTEGER PK | Internal identifier |
| `user_id` | INTEGER FK NULL | Referensi ke users (NULL jika user sudah dihapus) |
| `telegram_id` | INTEGER NULL | Telegram ID (disimpan langsung untuk backup) |
| `action` | TEXT | Nama tindakan: "docker.restart", "service.stop", dll |
| `target` | TEXT NULL | Target tindakan: nama kontainer, nama service, dll |
| `parameters` | TEXT NULL | Parameter tambahan dalam format JSON |
| `result_status` | TEXT | Status hasil: pending, success, failed, denied |
| `error_message` | TEXT NULL | Pesan error jika gagal |
| `duration_ms` | INTEGER NULL | Durasi eksekusi dalam milidetik |
| `created_at` | TEXT | Timestamp tindakan dilakukan |

---

### 4.4 Tabel `scheduled_jobs`

Menyimpan semua tugas terjadwal yang didefinisikan melalui bot.

```sql
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
```

**Deskripsi Kolom:**

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| `id` | INTEGER PK | Internal identifier |
| `name` | TEXT | Nama deskriptif job |
| `description` | TEXT NULL | Deskripsi job |
| `job_type` | TEXT | Tipe: cron, interval, one_time |
| `cron_expression` | TEXT NULL | Ekspresi cron (untuk job_type=cron) |
| `interval_seconds` | INTEGER NULL | Interval dalam detik (untuk job_type=interval) |
| `run_at` | TEXT NULL | Waktu eksekusi (untuk job_type=one_time) |
| `action` | TEXT | Action yang dijalankan: "system.status_report", dll |
| `parameters` | TEXT NULL | Parameter dalam format JSON |
| `is_active` | INTEGER | 0=dinonaktifkan, 1=aktif |
| `created_by` | INTEGER FK NULL | User yang membuat job ini |
| `last_run_at` | TEXT NULL | Kapan terakhir dijalankan |
| `next_run_at` | TEXT NULL | Kapan jadwal berikutnya |
| `run_count` | INTEGER | Total berapa kali sudah dijalankan |
| `failure_count` | INTEGER | Total berapa kali gagal |

---

### 4.5 Tabel `job_run_logs`

Mencatat setiap eksekusi scheduled job untuk keperluan debugging dan audit.

```sql
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
```

---

### 4.6 Tabel `alert_configs`

Menyimpan konfigurasi threshold untuk sistem alert otomatis.

```sql
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
```

**Deskripsi Kolom:**

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| `metric_name` | TEXT | Nama metrik yang dipantau |
| `threshold_value` | REAL | Nilai ambang batas |
| `threshold_unit` | TEXT | Satuan: percent, bytes, count, seconds |
| `comparison_op` | TEXT | Operator: gt (>), gte (>=), lt (<), lte (<=), eq (=) |
| `cooldown_minutes` | INTEGER | Jeda minimum antar alert untuk metrik yang sama |
| `last_triggered_at` | TEXT NULL | Kapan terakhir kali alert ini dikirim |
| `trigger_count` | INTEGER | Total berapa kali alert ini terpicu |

---

### 4.7 Tabel `plugin_configs`

Menyimpan konfigurasi per-plugin yang dapat diubah melalui bot.

```sql
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
```

---

### 4.8 Tabel `migrations`

Tracking versi migrasi database yang sudah diterapkan.

```sql
CREATE TABLE IF NOT EXISTS migrations (
    id          INTEGER     PRIMARY KEY AUTOINCREMENT,
    version     INTEGER     NOT NULL UNIQUE,
    name        TEXT        NOT NULL,
    applied_at  TEXT        NOT NULL DEFAULT (datetime('now', 'utc'))
);
```

---

## 5. Indeks Database

```sql
-- users: pencarian berdasarkan telegram_id (paling sering)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id
    ON users(telegram_id);

-- users: filter berdasarkan role untuk distribusi alert
CREATE INDEX IF NOT EXISTS idx_users_role_active
    ON users(role, is_active);

-- sessions: lookup session berdasarkan user_id
CREATE INDEX IF NOT EXISTS idx_sessions_user_id
    ON sessions(user_id);

-- sessions: cleanup sesi kedaluwarsa
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
    ON sessions(expires_at)
    WHERE expires_at IS NOT NULL;

-- audit_logs: query log berdasarkan user (paling sering)
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id_created_at
    ON audit_logs(user_id, created_at DESC);

-- audit_logs: query log berdasarkan action type
CREATE INDEX IF NOT EXISTS idx_audit_logs_action
    ON audit_logs(action, created_at DESC);

-- audit_logs: filter berdasarkan result status
CREATE INDEX IF NOT EXISTS idx_audit_logs_result_status
    ON audit_logs(result_status, created_at DESC);

-- scheduled_jobs: query job aktif
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_active
    ON scheduled_jobs(is_active, next_run_at);

-- job_run_logs: query log berdasarkan job
CREATE INDEX IF NOT EXISTS idx_job_run_logs_job_id
    ON job_run_logs(job_id, started_at DESC);

-- alert_configs: query konfigurasi alert aktif
CREATE INDEX IF NOT EXISTS idx_alert_configs_active
    ON alert_configs(is_active, metric_name);

-- plugin_configs: query berdasarkan nama plugin
CREATE INDEX IF NOT EXISTS idx_plugin_configs_plugin_name
    ON plugin_configs(plugin_name);

-- migrations: pencarian berdasarkan versi
CREATE UNIQUE INDEX IF NOT EXISTS idx_migrations_version
    ON migrations(version);
```

---

## 6. Strategi Migrasi

### Alur Migrasi Database

```
Aplikasi Start
     |
     v
DatabaseManager.initialize()
     |
     v
Cek tabel 'migrations' ada?
     |
     +-- Tidak -> Buat tabel migrations + jalankan migrasi 0001
     |
     +-- Ya -> Baca versi migrasi tertinggi yang sudah diterapkan
              |
              v
         Scan folder migrations/ untuk file .sql
              |
              v
         Jalankan semua migrasi dengan versi > versi saat ini
         (secara berurutan, dalam transaksi)
              |
              v
         Catat setiap migrasi yang berhasil ke tabel migrations
```

### Konvensi Penamaan File Migrasi

```
Format: {NNNN}_{deskripsi_singkat}.sql
Contoh:
  0001_initial_schema.sql
  0002_add_sessions_table.sql
  0003_add_alert_cooldown_column.sql
  0004_add_plugin_configs_table.sql
```

### Aturan Migrasi

1. Migrasi hanya berisi operasi `CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX`.
2. Migrasi **tidak boleh** berisi `DROP TABLE` atau `DROP COLUMN` tanpa konfirmasi eksplisit.
3. Setiap migrasi harus bersifat idempotent (gunakan `IF NOT EXISTS`).
4. Setiap migrasi dijalankan dalam transaksi. Jika gagal, seluruh transaksi di-rollback.
5. Tidak ada perubahan data (DML) dalam file migrasi.

---

## 7. Query Patterns Umum

### Mendapatkan User Berdasarkan Telegram ID

```sql
SELECT id, telegram_id, username, full_name, role, is_active, is_blocked, alert_enabled
FROM users
WHERE telegram_id = ?
LIMIT 1;
```

### Mencatat Audit Log

```sql
INSERT INTO audit_logs (user_id, telegram_id, action, target, parameters, result_status)
VALUES (?, ?, ?, ?, ?, 'pending');
```

### Update Status Audit Log

```sql
UPDATE audit_logs
SET result_status = ?, error_message = ?, duration_ms = ?
WHERE id = ?;
```

### Mendapatkan Alert Configs yang Aktif

```sql
SELECT id, metric_name, threshold_value, comparison_op, cooldown_minutes, last_triggered_at
FROM alert_configs
WHERE is_active = 1;
```

### Mendapatkan Pengguna yang Menerima Alert

```sql
SELECT telegram_id
FROM users
WHERE is_active = 1
  AND is_blocked = 0
  AND alert_enabled = 1
  AND role IN ('super_admin', 'admin', 'operator');
```

### Mendapatkan Riwayat Audit Log User

```sql
SELECT al.action, al.target, al.result_status, al.created_at
FROM audit_logs al
WHERE al.user_id = ?
ORDER BY al.created_at DESC
LIMIT 20;
```

---

## 8. Konfigurasi SQLite

Konfigurasi SQLite yang diterapkan saat koneksi dibuka:

```sql
-- WAL mode untuk performa lebih baik pada concurrent read
PRAGMA journal_mode = WAL;

-- Sinkronisasi normal (aman, lebih cepat dari FULL)
PRAGMA synchronous = NORMAL;

-- Cache size: 32MB
PRAGMA cache_size = -32000;

-- Aktifkan foreign key constraint enforcement
PRAGMA foreign_keys = ON;

-- Busy timeout: 5 detik sebelum error pada lock contention
PRAGMA busy_timeout = 5000;

-- Aktifkan mmap untuk performa baca lebih baik
PRAGMA mmap_size = 134217728;
```

---

## 9. Strategi Backup Database

### Backup Harian Otomatis

```
Setiap hari jam 02:00 UTC:
1. Bot menjalankan scheduled job: backup_database
2. Jalankan SQLite VACUUM INTO '/var/lib/serverinka/backups/guardian_YYYYMMDD.db'
3. Compress dengan gzip: guardian_YYYYMMDD.db.gz
4. Simpan 7 backup terakhir (hapus yang lebih lama)
5. Opsional: upload ke Google Drive / S3 (jika plugin dikonfigurasi)
```

### Backup Manual via Bot

```
Admin kirim /backup db
Bot jalankan backup segera
Bot kirim file backup ke admin via Telegram (jika ukuran < 50MB)
```

### Restore Database

```
1. Hentikan bot: systemctl stop serverinka-guardian
2. Salin backup ke lokasi database: cp guardian_YYYYMMDD.db /var/lib/serverinka/guardian.db
3. Verifikasi integritas: sqlite3 guardian.db "PRAGMA integrity_check;"
4. Jalankan kembali bot: systemctl start serverinka-guardian
```

---

## 10. Panduan Migrasi ke PostgreSQL

### Perubahan yang Diperlukan

| Aspek | SQLite | PostgreSQL |
|-------|--------|------------|
| Driver | aiosqlite | asyncpg |
| Integer PK | INTEGER AUTOINCREMENT | BIGSERIAL / GENERATED ALWAYS AS IDENTITY |
| Boolean | INTEGER (0/1) | BOOLEAN (TRUE/FALSE) |
| Timestamp | TEXT (ISO 8601) | TIMESTAMPTZ |
| JSON | TEXT | JSONB |
| Auto timestamp | datetime('now', 'utc') | NOW() AT TIME ZONE 'UTC' |

### Langkah Migrasi

1. Export seluruh data dari SQLite menggunakan script migrasi.
2. Ubah skema DDL ke PostgreSQL syntax.
3. Import data menggunakan PostgreSQL COPY atau INSERT.
4. Verifikasi integritas data.
5. Ganti driver di `core/database.py` dari `aiosqlite` ke `asyncpg`.
6. Update `DatabaseManager` untuk mendukung connection pool asyncpg.
7. Update query yang menggunakan `?` placeholder menjadi `$1, $2, ...` (PostgreSQL style).

### Abstraksi yang Mempermudah Migrasi

Seluruh query SQL dikelola dalam file `repository.py` masing-masing modul. Dengan demikian, migrasi driver database hanya memerlukan perubahan pada:
- `core/database.py` — connection management
- Seluruh `repository.py` — ganti placeholder style

Tidak ada perubahan pada layer `handlers.py`, `service.py`, atau `plugin.py`.

---

## 11. Keputusan Desain

### Mengapa Tidak Menggunakan UUID sebagai Primary Key?

SQLite mengimplementasikan UUID sebagai TEXT, yang lebih lambat untuk join dan index dibandingkan INTEGER. Untuk skala proyek ini (ribuan, bukan jutaan record), INTEGER AUTOINCREMENT adalah pilihan yang tepat. Jika migrasi ke PostgreSQL dilakukan, dapat diubah ke UUID dengan satu migrasi.

### Mengapa Menyimpan `telegram_id` di `audit_logs` Selain FK ke `users`?

Jika user dihapus dari sistem (meski jarang terjadi), record audit log tetap memiliki konteks tentang siapa yang melakukan tindakan. Ini penting untuk forensik dan compliance.

### Mengapa Tidak Ada Tabel Terpisah untuk Notification History?

Notification alert dicatat di `audit_logs` dengan action type "alert.sent". Ini mengurangi jumlah tabel dan menjaga audit trail tetap terpusat.

### Mengapa `alert_configs` Menggunakan `cooldown_minutes`?

Tanpa cooldown, setiap kali alert loop berjalan (setiap 60 detik), dan metrik masih di atas threshold, alert akan terus dikirim. Cooldown mencegah spam notifikasi untuk kondisi yang sudah diketahui admin.

---

## 12. Checklist Implementasi

### Schema

- [ ] Buat semua file SQL di folder `migrations/`
- [ ] File `0001_initial_schema.sql` berisi semua tabel dasar
- [ ] Semua constraint dan CHECK berhasil divalidasi
- [ ] Semua indeks dibuat dengan benar

### Migration System

- [ ] Implementasi `MigrationRunner` di `migrations/migration_runner.py`
- [ ] Migration runner dijalankan otomatis saat aplikasi start
- [ ] Migration runner idempotent (aman dijalankan berkali-kali)
- [ ] Unit test untuk migration runner dengan in-memory SQLite

### Repository Layer

- [ ] `UserRepository` dengan semua CRUD operations
- [ ] `AuditLogRepository` dengan metode insert dan query
- [ ] `SessionRepository` dengan CRUD dan cleanup expired sessions
- [ ] `ScheduledJobRepository` dengan CRUD dan query job aktif
- [ ] `AlertConfigRepository` dengan CRUD dan query config aktif
- [ ] `PluginConfigRepository` dengan get dan set operations
- [ ] Unit test untuk semua repository

### Database Manager

- [ ] `DatabaseManager` mengelola koneksi aiosqlite
- [ ] PRAGMA configurations diterapkan saat koneksi dibuka
- [ ] Context manager untuk transaksi
- [ ] Unit test dengan in-memory SQLite

---

*Referensi: [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [03_TECH_STACK.md](03_TECH_STACK.md) | [05_API_DESIGN.md](05_API_DESIGN.md)*
