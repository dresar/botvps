# Serverinka Guardian — Ringkasan Arsitektur & Prioritas Implementasi

> **Tanggal:** 2026-08-02
> **Status:** Dokumentasi Selesai — Siap Implementasi
> **Referensi:** docs/01_PRD.md s/d docs/10_DEVELOPMENT_RULES.md

---

## Ringkasan Arsitektur

### Identitas Proyek

**Serverinka Guardian** adalah bot Telegram open source yang berfungsi sebagai pusat kendali terpadu (*unified control plane*) untuk VPS Linux dan server pribadi. Berjalan sebagai systemd service, dikembangkan dengan Python 3.12+, arsitektur modular berbasis plugin.

---

### Peta Arsitektur (Ringkas)

```
[ Telegram User ]
       |
       v HTTPS
[ Telegram Bot API ]
       |
       v Long Polling / Webhook
+==========================================+
|         SERVERINKA GUARDIAN              |
|                                          |
|  BotGateway -> Middleware Stack          |
|                  |-> AuthMiddleware      |
|                  |-> RateLimitMiddleware |
|                  |-> AuditMiddleware     |
|                  v                       |
|             CommandRouter               |
|                  |                       |
|         +--------+---------+            |
|         |                  |            |
|    PluginManager       SchedulerEngine  |
|    EventBus            AlertLoop        |
|         |                               |
|    [Plugins Layer]                      |
|    system | service | docker |          |
|    notification | scheduler_ui | ...    |
|         |                               |
|    [Services & Repositories]            |
|    SystemService | DockerService |       |
|    ServiceManagerService | AuthService  |
|         |                               |
|    [Database: SQLite / aiosqlite]       |
|    users | audit_logs | sessions |      |
|    scheduled_jobs | alert_configs |     |
|    plugin_configs | migrations          |
+==========================================+
       |
[ Linux OS Layer ]
systemd | Docker | journald | psutil | subprocess
```

---

### Keputusan Arsitektur Kunci

| Keputusan | Pilihan | Alasan Singkat |
|-----------|---------|----------------|
| Pola arsitektur | Plugin-Based Monolith | Sederhana, cukup untuk target pengguna |
| Bahasa | Python 3.12+ | Ekosistem kaya, async matang, mudah dikontribusi |
| Bot library | python-telegram-bot v21+ | Paling matang, async native, komunitas besar |
| Database | SQLite + aiosqlite | Zero-config, mudah backup, migratable ke PostgreSQL |
| Package manager | uv | Cepat, lockfile native, menggantikan pip+venv |
| Linting/Format | Ruff + Mypy strict | Satu tool, cepat, type safety penuh |
| Scheduler | APScheduler | Matang, cron expression, persistensi ke SQLite |
| HTTP client | httpx | Async, API bersih, HTTP/2 ready |
| Antarmuka bot | Inline keyboard (HTML mode) | Fleksibel, mobile-first, update tanpa pesan baru |
| Autentikasi | Telegram User ID whitelist | Permanen, tidak dapat dipalsukan, zero-friction |
| Service runtime | systemd | Native di target OS, auto-restart, journald |

---

## Daftar Pekerjaan Implementasi Berdasarkan Prioritas

### FASE 0 — Fondasi (Mulai dari sini)

Semua pekerjaan di fase ini harus diselesaikan sebelum ada kode fitur yang ditulis.

```
PRIORITAS KRITIS:

[F0-1] Setup Repositori & Toolchain
  - Inisialisasi repositori dengan struktur folder yang benar
  - Konfigurasi pyproject.toml (dependency, ruff, mypy, pytest)
  - Buat .env.example dengan semua variabel terdokumentasi
  - Buat .gitignore
  - Buat .python-version (3.12)
  - Setup GitHub Actions: lint + test workflow
  - Buat LICENSE (MIT)
  - Buat README.md awal
  Estimasi: 1 hari

[F0-2] Core Infrastructure
  - guardian/__main__.py (entry point)
  - guardian/core/config.py (GuardianSettings dengan pydantic-settings)
  - guardian/core/exceptions.py (seluruh hierarchy exception)
  - guardian/interfaces/base_plugin.py (BasePlugin abstract class)
  - guardian/interfaces/base_service.py (BaseService abstract class)
  - guardian/interfaces/base_repository.py (BaseRepository abstract class)
  Estimasi: 1-2 hari

[F0-3] Database Foundation
  - guardian/core/database.py (DatabaseManager dengan aiosqlite)
  - guardian/migrations/migration_runner.py
  - guardian/migrations/0001_initial_schema.sql (semua tabel dari 04_DATABASE_DESIGN.md)
  - Unit test untuk database manager dan migration runner
  Estimasi: 1-2 hari

[F0-4] Authentication System
  - guardian/core/auth_service.py (AuthService)
  - guardian/plugins/user_manager/repository.py (UserRepository)
  - Super admin bootstrap dari env var saat startup
  - Unit test untuk AuthService (semua skenario: auth, deny, block)
  Estimasi: 1-2 hari
```

---

### FASE 1 — Core Engine (P0 — Blokir semua fitur)

```
PRIORITAS TINGGI:

[F1-1] Event Bus
  - guardian/core/event_bus.py
  - Async pub/sub dengan isolasi error per subscriber
  - Unit test untuk semua skenario (publish, subscribe, subscriber error)
  Estimasi: 1 hari

[F1-2] Plugin Manager
  - guardian/core/plugin_manager.py
  - Auto-discovery plugin dari folder plugins/
  - Dependency resolution dan sorting
  - Lifecycle management (setup, teardown)
  - Command registration registry
  - Callback registration registry
  - Error isolation saat plugin gagal
  - Unit test komprehensif
  Estimasi: 2-3 hari

[F1-3] Bot Gateway
  - guardian/core/bot_gateway.py
  - Koneksi ke Telegram API (long polling)
  - Middleware chain (Auth, RateLimit, Audit)
  - Command router
  - Message builder helpers
  - Global error handler
  - Unit test dengan mock Telegram API
  Estimasi: 2 hari

[F1-4] Scheduler Engine
  - guardian/core/scheduler.py
  - APScheduler dengan asyncio
  - Persistensi job ke database
  - API untuk plugin mendaftarkan job
  - Alert loop dasar
  - Unit test
  Estimasi: 1-2 hari

[F1-5] Application Engine
  - guardian/core/engine.py (ApplicationContext, startup, shutdown)
  - Orkestrasi semua komponen core
  - Graceful shutdown (SIGTERM/SIGINT)
  - Integration test: bot dapat start dan shutdown cleanly
  Estimasi: 1 hari
```

---

### FASE 2 — Plugin Core (P0 — MVP)

```
PRIORITAS TINGGI:

[F2-1] Plugin: System Monitor
  - plugins/system/plugin.py
  - plugins/system/service.py (SystemService: CPU, RAM, Disk, Network, Proses)
  - plugins/system/handlers.py (status, cpu, ram, disk, net, proc, reboot, shutdown)
  - plugins/system/keyboards.py (semua keyboard untuk system plugin)
  - plugins/system/messages.py (semua template pesan)
  - Unit test untuk SystemService (mock psutil)
  - Unit test untuk handlers
  Estimasi: 3 hari

[F2-2] Plugin: Service Manager (systemd)
  - plugins/service_manager/plugin.py
  - plugins/service_manager/service.py (ServiceManagerService)
  - plugins/service_manager/handlers.py (list, status, start, stop, restart, log)
  - Subprocess sandbox untuk systemctl dan journalctl
  - Input validation untuk service name
  - Unit test
  Estimasi: 2-3 hari

[F2-3] Plugin: Docker Manager
  - plugins/docker/plugin.py
  - plugins/docker/service.py (DockerService)
  - plugins/docker/handlers.py (list, detail, start, stop, restart, log, stats, images)
  - Graceful degradation jika Docker tidak tersedia
  - Input validation untuk container name
  - Unit test (mock docker-py)
  Estimasi: 3 hari

[F2-4] Plugin: Notification & Alert
  - plugins/notification/plugin.py
  - plugins/notification/service.py
  - plugins/notification/repository.py (AlertConfigRepository)
  - plugins/notification/handlers.py (list, set, test, toggle)
  - Alert loop integration dengan SchedulerEngine
  - Default alert configs saat instalasi
  - Unit test
  Estimasi: 2-3 hari
```

---

### FASE 3 — Plugin Sekunder & UX (P1)

```
PRIORITAS SEDANG:

[F3-1] Plugin: Scheduler UI
  - Antarmuka Telegram untuk mengelola scheduled jobs
  - List, add (interactive), delete, toggle jadwal
  - Laporan berkala terjadwal
  Estimasi: 2 hari

[F3-2] Plugin: User Manager
  - Antarmuka Telegram untuk mengelola pengguna
  - List, add, role change, deactivate
  Estimasi: 1-2 hari

[F3-3] Plugin: Audit Viewer
  - Tampilkan audit log melalui bot
  - Pagination untuk log yang panjang
  - Filter berdasarkan user
  Estimasi: 1 hari

[F3-4] Plugin: Settings
  - Konfigurasi bot melalui Telegram
  - Ubah bahasa, threshold default, dll
  Estimasi: 1 hari

[F3-5] UX Polish
  - Implementasi semua format pesan dari 08_TELEGRAM_BOT.md
  - Progress bar yang konsisten
  - Semua emoji guideline diterapkan
  - Pagination untuk semua daftar
  - Confirmation pattern untuk semua operasi berbahaya
  Estimasi: 2 hari
```

---

### FASE 4 — Deployment & Kualitas (P0 untuk Release)

```
PRIORITAS KRITIS SEBELUM RELEASE:

[F4-1] Deployment Scripts
  - scripts/setup.sh (instalasi production di Debian 12)
  - scripts/update.sh (update ke versi terbaru)
  - scripts/backup.sh (backup manual)
  - scripts/restore.sh (restore dari backup)
  - scripts/serverinka-guardian.service (systemd unit file)
  - scripts/sudoers.d/serverinka (sudo rules)
  - Test di Debian 12 fresh install
  - Test di Ubuntu 22.04 fresh install
  Estimasi: 2-3 hari

[F4-2] Backup System
  - Scheduled backup job (database harian)
  - Cleanup backup lama
  - Backup via bot command
  Estimasi: 1 hari

[F4-3] Test Coverage
  - Pastikan coverage > 80% untuk semua modul core
  - Pastikan coverage > 80% untuk semua plugin
  - Integration tests untuk alur utama
  Estimasi: 2-3 hari

[F4-4] Dokumentasi Pengguna
  - README.md lengkap (instalasi, konfigurasi, penggunaan)
  - CONTRIBUTING.md (panduan kontributor)
  - Plugin development guide
  Estimasi: 1-2 hari
```

---

### FASE 5 — Plugin Ekosistem (v1.1, Setelah Release v1.0)

```
PRIORITAS RENDAH (Post-release):

[F5-1] Plugin: Nginx Manager
  - Kelola virtual host Nginx
  - Status, reload, test konfigurasi
  Estimasi: 2-3 hari

[F5-2] Plugin: Firewall (UFW)
  - Tampilkan rules, tambah, hapus rule
  - Status UFW
  Estimasi: 2 hari

[F5-3] Plugin: Fail2ban Monitor
  - Tampilkan status jail
  - List banned IPs
  - Unban IP
  Estimasi: 2 hari

[F5-4] Plugin: SSH Key Manager
  - List authorized_keys
  - Tambah, hapus key
  Estimasi: 1-2 hari

[F5-5] AI Gateway
  - Abstraksi provider AI
  - Analisis log dengan LLM
  - Provider: OpenAI, Gemini, Ollama
  Estimasi: 3-4 hari
```

---

## Urutan Implementasi yang Direkomendasikan

```
MINGGU 1:
  F0-1 Setup + F0-2 Core Infrastructure + F0-3 Database + F0-4 Auth

MINGGU 2:
  F1-1 Event Bus + F1-2 Plugin Manager + F1-3 Bot Gateway

MINGGU 3:
  F1-4 Scheduler + F1-5 Engine + F2-1 System Plugin

MINGGU 4:
  F2-2 Service Manager Plugin + F2-3 Docker Plugin

MINGGU 5:
  F2-4 Notification Plugin + F3-1 Scheduler UI + F3-2 User Manager

MINGGU 6:
  F3-3 Audit + F3-4 Settings + F3-5 UX Polish

MINGGU 7-8:
  F4-1 Deployment Scripts + F4-2 Backup + F4-3 Testing + F4-4 Docs

RELEASE v1.0
```

---

## Dependency Antar Komponen

```
Config <- (semua komponen bergantung pada ini)
Database <- Migration <- (semua repository)
AuthService <- UserRepository <- Database
EventBus <- (semua plugin)
PluginManager <- EventBus, AuthService, Database
BotGateway <- PluginManager, AuthService
SchedulerEngine <- Database, EventBus
Engine <- semua komponen di atas

Plugin: System <- SystemService <- psutil, subprocess
Plugin: Service <- ServiceManagerService <- subprocess (systemctl)
Plugin: Docker <- DockerService <- docker-py
Plugin: Notification <- AlertConfigRepository, SchedulerEngine
Plugin: SchedulerUI <- SchedulerEngine, Database
Plugin: UserManager <- UserRepository
Plugin: AuditViewer <- AuditLogRepository
```

---

## Metrik Keberhasilan Implementasi

| Metrik | Target v1.0 |
|--------|-------------|
| Test coverage (core) | > 90% |
| Test coverage (plugins) | > 80% |
| Linting errors | 0 |
| Mypy errors | 0 |
| Waktu instalasi dari nol | < 15 menit |
| Waktu respons perintah baca | < 2 detik |
| Bot recovery setelah crash | < 10 detik |
| File Python > 500 baris | 0 |

---

*Dokumen ini adalah titik awal implementasi Serverinka Guardian.*
*Mulai dari F0-1 dan ikuti urutan yang direkomendasikan.*
