# 03 — Tech Stack
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [01_PRD.md](01_PRD.md) | [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Runtime & Bahasa Pemrograman](#2-runtime--bahasa-pemrograman)
3. [Framework Bot Telegram](#3-framework-bot-telegram)
4. [Database & ORM](#4-database--orm)
5. [Scheduler & Task Queue](#5-scheduler--task-queue)
6. [Dependency Manager & Packaging](#6-dependency-manager--packaging)
7. [Logging & Monitoring](#7-logging--monitoring)
8. [Konfigurasi & Secrets](#8-konfigurasi--secrets)
9. [Pengembangan & Testing](#9-pengembangan--testing)
10. [Linting, Formatting & Type Checking](#10-linting-formatting--type-checking)
11. [Sistem Integrasi Eksternal](#11-sistem-integrasi-eksternal)
12. [Deployment & Infrastruktur](#12-deployment--infrastruktur)
13. [Struktur Package & Modul](#13-struktur-package--modul)
14. [Daftar Lengkap Dependensi](#14-daftar-lengkap-dependensi)
15. [Keputusan Desain](#15-keputusan-desain)
16. [Checklist Implementasi](#16-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan seluruh teknologi yang digunakan dalam proyek Serverinka Guardian beserta alasan pemilihannya. Setiap teknologi dipilih dengan mempertimbangkan kematangan, kompatibilitas, performa, kemudahan kontribusi, dan keselarasan dengan tujuan proyek.

---

## 2. Runtime & Bahasa Pemrograman

### Python 3.12+

**Versi minimum:** Python 3.12
**Versi rekomendasi:** Python 3.12.x (stable LTS)

**Alasan pemilihan:**
- Ekosistem library yang sangat kaya untuk manajemen sistem, jaringan, dan API.
- Dukungan `asyncio` native yang matang untuk operasi I/O-bound.
- `python-telegram-bot` sebagai library bot yang paling matang dan aktif dikembangkan.
- Type hints sejak Python 3.5, semakin kuat di 3.12 (PEP 695, improved generics).
- Mudah dipelajari oleh kontributor komunitas.
- `psutil` untuk akses metrik sistem lintas platform.

**Fitur Python 3.12 yang digunakan:**
- `asyncio` dengan `TaskGroup` untuk konkurensi yang lebih aman.
- Pesan error yang lebih baik untuk debugging.
- `f-string` debugging dengan `=` operator.
- `tomllib` built-in untuk membaca TOML.
- Improved `typing` module.

---

## 3. Framework Bot Telegram

### python-telegram-bot v21+

**Package:** `python-telegram-bot[job-queue]`

**Alasan pemilihan:**
- Library bot Telegram paling matang dan berdokumentasi lengkap untuk Python.
- Dukungan native asyncio dengan `Application` pattern.
- Built-in `JobQueue` untuk tugas terjadwal sederhana.
- Abstraksi tingkat tinggi untuk handler, filter, dan conversation.
- Komunitas aktif dan update rutin mengikuti perubahan Telegram API.
- Mendukung long polling dan webhook.

**Komponen yang digunakan:**
- `Application` — Orkestrasi bot utama.
- `CommandHandler` — Menangani perintah `/command`.
- `CallbackQueryHandler` — Menangani inline keyboard button.
- `MessageHandler` — Menangani pesan teks biasa.
- `ConversationHandler` — Multi-step conversation flow.
- `Filters` — Filter update berdasarkan tipe dan konten.

---

## 4. Database & ORM

### SQLite via aiosqlite

**Primary:** SQLite 3 (default, zero-config)
**Future migration target:** PostgreSQL 15+

**Package:** `aiosqlite`

**Alasan pemilihan SQLite:**
- Zero konfigurasi, tidak perlu install server database terpisah.
- File-based, mudah di-backup (salin satu file).
- Performa sangat baik untuk workload bot (read-heavy, write infrequent).
- WAL (Write-Ahead Logging) mode untuk konkurensi yang lebih baik.
- Tersedia native di Python (sqlite3 stdlib).

**Alasan pemilihan aiosqlite:**
- Wrapper async untuk sqlite3, kompatibel dengan asyncio event loop.
- API identik dengan sqlite3, learning curve minimal.
- Memungkinkan operasi database tanpa memblok event loop.

**Strategi migrasi ke PostgreSQL:**
- Seluruh query ditulis menggunakan parameter binding standar (tidak ada syntax SQLite-specific selain tipe data).
- Migration manager dibuat agar kompatibel dengan kedua database.
- Untuk masa depan: ganti `aiosqlite` dengan `asyncpg` tanpa perubahan logika bisnis.

**Tidak menggunakan ORM (seperti SQLAlchemy) karena:**
- Menambah kompleksitas dan overhead tidak perlu untuk project ini.
- Raw SQL lebih transparan dan mudah di-audit.
- Lebih mudah dikontrol untuk optimasi query spesifik.
- Repository pattern digunakan sebagai abstraksi di atas raw SQL.

---

## 5. Scheduler & Task Queue

### APScheduler v3.x

**Package:** `APScheduler`

**Alasan pemilihan:**
- Library scheduling Python yang paling matang dan feature-complete.
- Mendukung cron expression, interval trigger, dan one-time date trigger.
- Mendukung asyncio job executor secara native.
- Dapat menyimpan jadwal ke database (SQLite/PostgreSQL) untuk persistensi.
- API yang bersih dan mudah dipahami.

**Komponen yang digunakan:**
- `AsyncIOScheduler` — Scheduler yang berjalan dalam event loop asyncio.
- `CronTrigger` — Untuk jadwal berbasis cron expression.
- `IntervalTrigger` — Untuk alert loop dengan interval tetap.
- `DateTrigger` — Untuk one-time scheduled task.
- `SQLAlchemyJobStore` — Persistensi jadwal ke database (via SQLite).

---

## 6. Dependency Manager & Packaging

### uv (Astral)

**Tool:** `uv`

**Alasan pemilihan:**
- Tool manajemen Python environment dan package yang sangat cepat (ditulis dalam Rust).
- Menggantikan pip + virtualenv + pip-tools dengan satu tool.
- Mendukung `pyproject.toml` sebagai sumber kebenaran dependency.
- Lockfile (`uv.lock`) untuk reproducible builds.
- Kompatibel dengan pip dan PyPI.

**Alternatif yang dipertimbangkan:**
- `pip` + `venv`: Terlalu primitif, tidak ada lockfile.
- `poetry`: Bagus tapi lebih lambat dari uv.
- `pdm`: Opsi bagus tapi komunitas lebih kecil.

**File konfigurasi:**

```
pyproject.toml      <- Sumber kebenaran dependency dan metadata proyek
uv.lock             <- Lockfile untuk reproducible install
.python-version     <- Menentukan versi Python yang digunakan (3.12.x)
```

---

## 7. Logging & Monitoring

### Logging Standard Library + Structlog

**Packages:** `structlog`, `rich` (untuk dev output)

**Arsitektur logging:**
- `structlog` untuk structured logging dengan output JSON di production.
- Python standard `logging` sebagai backend.
- `rich` untuk output log yang mudah dibaca saat development.
- journald otomatis menangkap stdout/stderr dari systemd service.

**Log levels yang digunakan:**
- `DEBUG` — Detail debugging saat development.
- `INFO` — Event penting: startup, shutdown, plugin loaded, command executed.
- `WARNING` — Kejadian yang perlu diperhatikan tapi tidak error.
- `ERROR` — Error yang dapat di-recover.
- `CRITICAL` — Error yang menyebabkan shutdown.

**Format log production:**
```json
{
  "timestamp": "2026-08-02T12:00:00+07:00",
  "level": "INFO",
  "event": "command_executed",
  "user_id": 123456789,
  "command": "docker.list",
  "duration_ms": 342
}
```

**Lokasi log:**
- stdout/stderr -> journald (dikelola systemd)
- File log: `/var/log/serverinka/guardian.log` (opsional, dikonfigurasi)
- Audit log: tersimpan di database tabel `audit_logs`

---

## 8. Konfigurasi & Secrets

### python-dotenv + Pydantic Settings

**Packages:** `python-dotenv`, `pydantic-settings`

**Alasan pemilihan:**
- `python-dotenv` untuk membaca file `.env` menjadi environment variables.
- `pydantic-settings` untuk validasi dan type-safe akses ke konfigurasi.
- Pydantic memberikan validasi tipe, nilai default, dan pesan error yang jelas.

**Arsitektur konfigurasi:**

```
/etc/serverinka/guardian.env     <- File konfigurasi production (dilindungi)
.env.example                     <- Template konfigurasi (di repositori)
.env                             <- Konfigurasi lokal developer (di .gitignore)
```

**Contoh struktur konfigurasi (pydantic model):**
```
class GuardianSettings:
    telegram_bot_token: str
    telegram_admin_user_ids: list[int]
    database_path: str = "/var/lib/serverinka/guardian.db"
    log_level: str = "INFO"
    scheduler_alert_interval_seconds: int = 60
    rate_limit_commands_per_minute: int = 30
    ai_provider: str = "disabled"
    ai_api_key: str = ""
    docker_enabled: bool = True
```

---

## 9. Pengembangan & Testing

### Framework Testing: pytest

**Packages:** `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`

**Alasan pemilihan:**
- pytest adalah de facto standard testing framework di Python.
- `pytest-asyncio` untuk test fungsi async secara native.
- `pytest-cov` untuk laporan code coverage.
- `pytest-mock` untuk mocking dependensi eksternal.

**Strategi testing:**

```
Unit Tests
  -> Test setiap fungsi/method secara terisolasi
  -> Mock semua dependensi eksternal (Telegram API, Docker, OS calls)
  -> Target coverage: > 80% per modul

Integration Tests
  -> Test interaksi antar modul
  -> Menggunakan in-memory SQLite untuk database
  -> Mock Telegram API dengan PTB TestBot

End-to-End Tests
  -> Test alur lengkap dari command sampai respons
  -> Hanya untuk skenario kritikal (auth, plugin loading)
```

**Folder struktur test:**
```
tests/
  unit/
    core/
    plugins/
  integration/
  fixtures/
  conftest.py
```

---

## 10. Linting, Formatting & Type Checking

### Ruff (Linting & Formatting)

**Package:** `ruff`

**Alasan pemilihan:**
- Tool tunggal yang menggantikan flake8, isort, black, dan banyak linter lain.
- Sangat cepat (ditulis dalam Rust).
- Konfigurasi di `pyproject.toml`.
- Mendukung auto-fix untuk banyak error.

**Konfigurasi Ruff:**
- Line length: 100 karakter.
- Target Python version: 3.12.
- Rules enabled: E, W, F, I, B, C4, UP, N, ANN (type annotation rules).

### Mypy (Type Checking)

**Package:** `mypy`

**Alasan pemilihan:**
- Type checker paling matang untuk Python.
- Memastikan type hints yang ditulis benar-benar valid.
- Dapat menemukan bug potensial sebelum runtime.

**Konfigurasi Mypy:**
- `strict = true` untuk enforcement ketat.
- `python_version = "3.12"`.

---

## 11. Sistem Integrasi Eksternal

### Docker SDK for Python

**Package:** `docker`

**Kegunaan:** Manajemen kontainer Docker (list, start, stop, logs, stats).

### httpx (HTTP Client Async)

**Package:** `httpx`

**Kegunaan:**
- HTTP requests ke API eksternal (Cloudflare, GitHub, AI Provider).
- Lebih baik dari `requests` untuk async code karena fully async.
- Alternatif modern untuk `aiohttp` dengan API yang lebih bersih.

### psutil (System Metrics)

**Package:** `psutil`

**Kegunaan:** Mengambil metrik sistem: CPU, RAM, Disk, Network, Proses.

---

## 12. Deployment & Infrastruktur

### systemd

- Mengelola lifecycle bot (start, stop, restart, auto-start).
- Penanganan crash dengan automatic restart.
- Log management via journald.
- Resource limits (CPU, memory) via cgroup.

### Target OS

| OS | Versi | Status |
|----|-------|--------|
| Debian | 12 (Bookworm) | Primary target |
| Ubuntu Server | 22.04 LTS | Didukung |
| Ubuntu Server | 24.04 LTS | Didukung |

---

## 13. Struktur Package & Modul

```
serverinka-guardian/
|
|-- guardian/                    <- Package utama aplikasi
|   |-- __init__.py
|   |-- __main__.py              <- Entry point: python -m guardian
|   |
|   |-- core/                    <- Core engine (TIDAK DIUBAH oleh plugin)
|   |   |-- __init__.py
|   |   |-- engine.py            <- Application lifecycle
|   |   |-- bot_gateway.py       <- Telegram API wrapper
|   |   |-- plugin_manager.py    <- Plugin loader & registry
|   |   |-- auth_service.py      <- Authentication & authorization
|   |   |-- scheduler.py         <- Scheduler engine
|   |   |-- event_bus.py         <- Async event bus
|   |   |-- database.py          <- Database connection manager
|   |   |-- config.py            <- Configuration loader
|   |   `-- exceptions.py        <- Custom exception classes
|   |
|   |-- interfaces/              <- Abstraksi yang diimplementasi plugin
|   |   |-- __init__.py
|   |   |-- base_plugin.py       <- BasePlugin abstract class
|   |   |-- base_service.py      <- BaseService abstract class
|   |   `-- base_repository.py   <- BaseRepository abstract class
|   |
|   |-- utils/                   <- Utility functions (stateless)
|   |   |-- __init__.py
|   |   |-- formatters.py        <- Format angka, waktu, bytes
|   |   |-- validators.py        <- Input validation
|   |   |-- message_builder.py   <- Telegram message builder
|   |   `-- keyboard_builder.py  <- InlineKeyboard builder
|   |
|   |-- plugins/                 <- Semua plugin (dapat ditambah/dikurangi)
|   |   |-- __init__.py
|   |   |
|   |   |-- system/              <- Plugin: System Monitor
|   |   |   |-- __init__.py
|   |   |   |-- plugin.py        <- Plugin entrypoint
|   |   |   |-- handlers.py      <- Command handlers
|   |   |   |-- service.py       <- System metrics service
|   |   |   `-- repository.py    <- Data access (jika diperlukan)
|   |   |
|   |   |-- service_manager/     <- Plugin: systemd Service Manager
|   |   |   |-- __init__.py
|   |   |   |-- plugin.py
|   |   |   |-- handlers.py
|   |   |   `-- service.py
|   |   |
|   |   |-- docker/              <- Plugin: Docker Manager
|   |   |   |-- __init__.py
|   |   |   |-- plugin.py
|   |   |   |-- handlers.py
|   |   |   `-- service.py
|   |   |
|   |   |-- notification/        <- Plugin: Alert & Notification
|   |   |   |-- __init__.py
|   |   |   |-- plugin.py
|   |   |   |-- handlers.py
|   |   |   |-- service.py
|   |   |   `-- repository.py
|   |   |
|   |   `-- scheduler_ui/        <- Plugin: Scheduler UI
|   |       |-- __init__.py
|   |       |-- plugin.py
|   |       |-- handlers.py
|   |       `-- service.py
|   |
|   `-- migrations/              <- Database migration files
|       |-- __init__.py
|       |-- 0001_initial.sql
|       |-- 0002_add_sessions.sql
|       `-- migration_runner.py
|
|-- plugins_community/           <- Folder untuk plugin komunitas (future)
|
|-- tests/                       <- Seluruh test
|   |-- unit/
|   |-- integration/
|   |-- fixtures/
|   `-- conftest.py
|
|-- docs/                        <- Dokumentasi teknis (10 file ini)
|
|-- scripts/                     <- Script operasional
|   |-- setup.sh                 <- Instalasi di VPS baru
|   |-- update.sh                <- Update bot ke versi terbaru
|   `-- backup.sh                <- Backup database dan konfigurasi
|
|-- pyproject.toml               <- Metadata, dependency, konfigurasi tool
|-- uv.lock                      <- Lockfile dependency
|-- .python-version              <- Target Python version
|-- .env.example                 <- Template konfigurasi
|-- .gitignore
|-- README.md
|-- CONTRIBUTING.md
|-- CHANGELOG.md
`-- LICENSE                      <- MIT License
```

---

## 14. Daftar Lengkap Dependensi

### Dependencies (Runtime)

```toml
[project.dependencies]
python-telegram-bot = {version = ">=21.0,<22.0", extras = ["job-queue"]}
aiosqlite = ">=0.21.0"
APScheduler = ">=3.10.0,<4.0"
psutil = ">=6.0.0"
python-dotenv = ">=1.0.0"
pydantic-settings = ">=2.0.0"
docker = ">=7.0.0"
httpx = ">=0.27.0"
structlog = ">=24.0.0"
rich = ">=13.0.0"
```

### Dev Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
    "types-psutil",
    "types-docker",
]
```

### Dependency yang Tidak Digunakan (dan Alasannya)

| Package | Alasan Tidak Digunakan |
|---------|----------------------|
| SQLAlchemy | Overhead tidak perlu, raw SQL lebih transparan |
| Celery | Terlalu berat, APScheduler sudah cukup |
| Redis | Tidak diperlukan untuk single-instance |
| FastAPI / Flask | Tidak ada web server, hanya bot Telegram |
| Alembic | Migration manual lebih kontrol untuk proyek ini |
| aiohttp | Digantikan oleh httpx yang lebih modern |
| requests | Tidak async, digantikan httpx |

---

## 15. Keputusan Desain

### Mengapa uv, bukan pip + venv?

uv jauh lebih cepat, memiliki lockfile native, dan menggabungkan fungsi pip, venv, dan pip-tools dalam satu alat. Untuk proyek yang ingin mudah dikontribusi, instalasi dependency yang cepat adalah keunggulan signifikan.

### Mengapa Ruff, bukan Black + flake8 + isort?

Ruff menggantikan ketiganya dengan satu tool yang 10-100x lebih cepat. Konfigurasi lebih sederhana (satu file `pyproject.toml`). Ini mengurangi kompleksitas toolchain pengembangan.

### Mengapa tidak menggunakan ORM?

Untuk proyek ini, raw SQL lebih transparan, mudah di-audit, dan tidak ada overhead mapping. Repository pattern menyediakan abstraksi yang cukup tanpa memerlukan ORM penuh.

### Mengapa httpx, bukan aiohttp?

httpx memiliki API yang lebih bersih, mendukung HTTP/2, dan memiliki mode sync dan async. Lebih mudah di-test dan di-mock dibandingkan aiohttp.

---

## 16. Checklist Implementasi

### Setup Proyek

- [ ] Inisialisasi proyek dengan `uv init`
- [ ] Konfigurasi `pyproject.toml` dengan semua dependency
- [ ] Konfigurasi Ruff di `pyproject.toml`
- [ ] Konfigurasi Mypy di `pyproject.toml`
- [ ] Setup `pytest` dengan `pytest.ini` atau konfigurasi di `pyproject.toml`
- [ ] Buat `.env.example` dengan semua variabel yang diperlukan
- [ ] Setup pre-commit hooks (ruff format, ruff check, mypy)

### Verifikasi

- [ ] `uv run python --version` menampilkan 3.12+
- [ ] `uv run pytest` dapat dijalankan tanpa error
- [ ] `uv run ruff check .` lulus tanpa error
- [ ] `uv run mypy .` lulus tanpa error
- [ ] Semua dependensi dapat diinstall di Debian 12 fresh install

---

*Referensi: [01_PRD.md](01_PRD.md) | [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [04_DATABASE_DESIGN.md](04_DATABASE_DESIGN.md)*
