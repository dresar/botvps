# 02 — Arsitektur Sistem
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [01_PRD.md](01_PRD.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Gambaran Arsitektur Tingkat Tinggi](#2-gambaran-arsitektur-tingkat-tinggi)
3. [Diagram Arsitektur Sistem](#3-diagram-arsitektur-sistem)
4. [Komponen Inti (Core Components)](#4-komponen-inti-core-components)
5. [Komponen Plugin (Plugin Components)](#5-komponen-plugin-plugin-components)
6. [Komponen Infrastruktur (Infrastructure Components)](#6-komponen-infrastruktur-infrastructure-components)
7. [Komponen Eksternal (External Components)](#7-komponen-eksternal-external-components)
8. [Alur Data (Data Flow)](#8-alur-data-data-flow)
9. [Arsitektur Lapisan (Layered Architecture)](#9-arsitektur-lapisan-layered-architecture)
10. [Arsitektur Deployment](#10-arsitektur-deployment)
11. [Keputusan Desain](#11-keputusan-desain)
12. [Checklist Implementasi](#12-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini menjelaskan keseluruhan arsitektur sistem Serverinka Guardian. Dokumen ini menjadi panduan bagi seluruh pengembang untuk memahami bagaimana komponen-komponen sistem berinteraksi satu sama lain, di mana setiap modul berada, dan bagaimana aliran data mengalir melalui sistem.

---

## 2. Gambaran Arsitektur Tingkat Tinggi

Serverinka Guardian menggunakan arsitektur **Plugin-Based Monolith** yang berjalan sebagai **single process** di VPS target. Arsitektur ini memiliki karakteristik:

- **Satu proses utama** yang berjalan sebagai systemd service.
- **Core Engine** yang kecil dan stabil sebagai pusat orkestrasi.
- **Plugin Manager** yang memuat, mengelola, dan mengisolasi plugin.
- **Event Bus** untuk komunikasi antar-plugin tanpa coupling langsung.
- **Database tunggal** (SQLite) yang diakses oleh seluruh komponen.
- **Async-first** menggunakan asyncio Python untuk semua operasi I/O.

### Prinsip Arsitektur

| Prinsip | Implementasi |
|---------|-------------|
| Separation of Concerns | Setiap modul memiliki satu tanggung jawab |
| Dependency Inversion | Plugin bergantung pada abstraksi, bukan implementasi konkret |
| Open/Closed Principle | Sistem terbuka untuk ekstensi via plugin, tertutup untuk modifikasi core |
| Single Source of Truth | Konfigurasi di .env, state di database |
| Fail-Safe Default | Jika plugin error, core tetap berjalan |

---

## 3. Diagram Arsitektur Sistem

### 3.1 Diagram Komponen Utama

```
+==============================================================================+
|                         SERVERINKA GUARDIAN SYSTEM                           |
+==============================================================================+
|                                                                              |
|  +------------------+     HTTPS/Webhook     +------------------------+       |
|  |   TELEGRAM USER  | <-------------------> |   TELEGRAM BOT API    |       |
|  +------------------+                       | (api.telegram.org)    |       |
|                                             +----------+-------------+       |
|                                                        |                     |
|                                             Long Polling / Webhook           |
|                                                        |                     |
|  +=====================================================================+     |
|  |                    SERVERINKA GUARDIAN PROCESS                      |     |
|  |                                                                     |     |
|  |  +-------------------+        +--------------------------------+    |     |
|  |  |  BOT GATEWAY      |        |        CORE ENGINE             |    |     |
|  |  |                   |        |                                |    |     |
|  |  |  - Update Handler |------->|  - Application Lifecycle      |    |     |
|  |  |  - Router         |        |  - Context Manager            |    |     |
|  |  |  - Middleware Stack|        |  - Error Handler              |    |     |
|  |  |  - Rate Limiter   |        |  - Config Loader              |    |     |
|  |  +-------------------+        +----+---------------------------+    |     |
|  |                                    |                                |     |
|  |                    +---------------+---------------+               |     |
|  |                    |               |               |               |     |
|  |             +------v------+ +------v------+ +------v------+        |     |
|  |             |   PLUGIN    | |   AUTH      | | SCHEDULER   |        |     |
|  |             |   MANAGER   | |   SERVICE   | |   ENGINE    |        |     |
|  |             |             | |             | |             |        |     |
|  |             | - Loader    | | - Whitelist | | - Job Queue |        |     |
|  |             | - Registry  | | - RBAC      | | - Cron Jobs |        |     |
|  |             | - Lifecycle | | - Session   | | - Alert Loop|        |     |
|  |             | - Injector  | | - Audit Log | |             |        |     |
|  |             +------+------+ +------+------+ +------+------+        |     |
|  |                    |               |               |               |     |
|  |             +======+===============+===============+======+        |     |
|  |             |              EVENT BUS                      |        |     |
|  |             |   (Asyncio-based internal message broker)   |        |     |
|  |             +======+===============+===============+======+        |     |
|  |                    |               |               |               |     |
|  |     +--------------+-------+  +----+----+  +-------+-------+      |     |
|  |     |    PLUGIN LAYER      |  |   DB    |  | AI GATEWAY    |      |     |
|  |     |                      |  | LAYER   |  |               |      |     |
|  |     | +------------------+ |  |         |  | - Provider    |      |     |
|  |     | | Plugin: System   | |  | SQLite  |  |   Registry    |      |     |
|  |     | +------------------+ |  |         |  | - Prompt Mgr  |      |     |
|  |     | | Plugin: Service  | |  | (Future |  | - Response    |      |     |
|  |     | +------------------+ |  |  PgSQL) |  |   Parser      |      |     |
|  |     | | Plugin: Docker   | |  |         |  |               |      |     |
|  |     | +------------------+ |  +---------+  +-------+-------+      |     |
|  |     | | Plugin: Nginx    | |                       |               |     |
|  |     | +------------------+ |             External AI APIs          |     |
|  |     | | Plugin: Notif.   | |             (OpenAI, Gemini, etc.)    |     |
|  |     | +------------------+ |                                       |     |
|  |     | | Plugin: [Custom] | |                                       |     |
|  |     | +------------------+ |                                       |     |
|  |     +----------------------+                                       |     |
|  |                                                                     |     |
|  +=====================================================================+     |
|                                                                              |
|  +===========================+  +=========================================+  |
|  |   LINUX SYSTEM LAYER      |  |       EXTERNAL SERVICES LAYER          |  |
|  |                           |  |                                        |  |
|  | - systemd                 |  | - Cloudflare (DNS, Tunnel)             |  |
|  | - Docker Engine           |  | - GitHub (Webhook, Actions)            |  |
|  | - Nginx                   |  | - Google Drive (Backup)                |  |
|  | - UFW / iptables          |  | - AI Provider API                      |  |
|  | - Fail2ban                |  |                                        |  |
|  | - journald                |  +=========================================+  |
|  | - CasaOS                  |                                              |
|  +===========================+                                              |
|                                                                              |
+==============================================================================+
```

### 3.2 Diagram Alur Request Telegram

```
Telegram User
     |
     | Kirim pesan/command
     v
Telegram Bot API
     |
     | Deliver Update (Long Polling / Webhook)
     v
Bot Gateway (telegram_gateway.py)
     |
     | Parse Update -> Extract command & args
     v
Middleware Stack
     | AuthMiddleware: cek whitelist & session
     | RateLimitMiddleware: cek rate limit
     | AuditMiddleware: catat ke audit log
     v
Router (command_router.py)
     |
     | Route ke handler yang sesuai
     v
Plugin Handler
     |
     | Jalankan logika bisnis
     | Panggil SystemService / DockerService / dll
     v
Response Builder (message_builder.py)
     |
     | Format teks + inline keyboard
     v
Bot Gateway
     |
     | sendMessage ke Telegram API
     v
Telegram User menerima respons
```

---

## 4. Komponen Inti (Core Components)

### 4.1 Core Engine (`core/engine.py`)

Bertanggung jawab atas:
- Inisialisasi seluruh komponen sistem saat startup.
- Orkestrasi lifecycle bot (start, stop, restart).
- Penanganan sinyal OS (SIGTERM, SIGINT) untuk graceful shutdown.
- Manajemen context global yang tersedia untuk semua plugin.

**Interaksi:**
- Memuat `ConfigLoader` untuk mendapatkan konfigurasi.
- Menginisialisasi `DatabaseManager`.
- Menginisialisasi `PluginManager` dan memuat semua plugin.
- Menginisialisasi `BotGateway` dan menghubungkan ke Telegram API.
- Menginisialisasi `SchedulerEngine`.
- Memulai event loop asyncio.

### 4.2 Bot Gateway (`core/bot_gateway.py`)

Bertanggung jawab atas:
- Menerima update dari Telegram API via long polling atau webhook.
- Meneruskan update ke middleware stack.
- Mengirim respons ke Telegram API.
- Mengelola koneksi ke Telegram API dengan auto-reconnect.

### 4.3 Plugin Manager (`core/plugin_manager.py`)

Bertanggung jawab atas:
- Menemukan plugin di folder `plugins/`.
- Memuat dan menginisialisasi plugin secara berurutan berdasarkan dependensi.
- Menyediakan registry untuk command handler.
- Mengirimkan event ke plugin yang terdaftar.
- Menangani kegagalan plugin secara terisolasi.

### 4.4 Auth Service (`core/auth_service.py`)

Bertanggung jawab atas:
- Memvalidasi User ID Telegram terhadap whitelist.
- Mengelola sesi pengguna aktif.
- Menyediakan informasi role pengguna kepada komponen lain.
- Mencatat semua event autentikasi ke audit log.

### 4.5 Scheduler Engine (`core/scheduler.py`)

Bertanggung jawab atas:
- Menjalankan job terjadwal berbasis cron expression.
- Menjalankan alert loop untuk memantau metrik sistem.
- Menyimpan dan memulihkan jadwal dari database.
- Menyediakan API untuk plugin mendaftarkan job terjadwal.

### 4.6 Database Manager (`core/database.py`)

Bertanggung jawab atas:
- Mengelola koneksi ke SQLite database.
- Menjalankan migrasi database saat startup.
- Menyediakan connection pool (untuk masa depan dengan PostgreSQL).
- Menyediakan metode query yang type-safe menggunakan aiosqlite.

### 4.7 Config Loader (`core/config.py`)

Bertanggung jawab atas:
- Membaca dan memvalidasi konfigurasi dari file `.env`.
- Menyediakan akses terpusat ke konfigurasi seluruh sistem.
- Memberikan nilai default yang aman untuk semua konfigurasi.
- Memvalidasi konfigurasi yang dibutuhkan saat startup.

### 4.8 Event Bus (`core/event_bus.py`)

Bertanggung jawab atas:
- Menyediakan sistem publish/subscribe async antar komponen.
- Memastikan plugin berkomunikasi melalui event, bukan direct call.
- Mencatat event untuk debugging.
- Menangani kegagalan subscriber secara terisolasi.

---

## 5. Komponen Plugin (Plugin Components)

Semua plugin berada di folder `plugins/` dan mengikuti antarmuka `BasePlugin`.

### 5.1 Plugin System (`plugins/system/`)

Berinteraksi dengan:
- `psutil` untuk mengambil metrik CPU, RAM, Disk, Network.
- `subprocess` untuk menjalankan perintah sistem (uptime, uname, dll).

### 5.2 Plugin Service (`plugins/service/`)

Berinteraksi dengan:
- `systemctl` via subprocess yang ter-sandbox.
- `journalctl` untuk mengambil log layanan.

### 5.3 Plugin Docker (`plugins/docker/`)

Berinteraksi dengan:
- Docker SDK for Python (`docker` library).
- Docker Compose CLI via subprocess.

### 5.4 Plugin Notification (`plugins/notification/`)

Berinteraksi dengan:
- Bot Gateway untuk mengirim pesan otomatis.
- Scheduler Engine untuk mendaftarkan alert loop.
- Database untuk menyimpan konfigurasi threshold.

### 5.5 Plugin Scheduler (`plugins/scheduler_ui/`)

Berinteraksi dengan:
- Scheduler Engine untuk mendaftarkan dan mengelola job.
- Database untuk persistensi jadwal.

---

## 6. Komponen Infrastruktur (Infrastructure Components)

### 6.1 systemd Service

Bot berjalan sebagai systemd service (`serverinka-guardian.service`).

```
systemd
  |-- Manages lifecycle: start, stop, restart
  |-- Auto-restart on failure (RestartSec=10)
  |-- Captures stdout/stderr ke journald
  |-- Runs as dedicated non-root user (serverinka)
  |-- Environment file dari /etc/serverinka/guardian.env
```

### 6.2 Linux System Integration

```
Bot Process
  |
  |-- psutil          -> /proc/stat, /proc/meminfo, /proc/net/dev
  |-- subprocess      -> systemctl, journalctl, apt, docker
  |-- os module       -> file system operations
  |-- socket module   -> network info
```

### 6.3 Database (SQLite / PostgreSQL)

```
SQLite File: /var/lib/serverinka/guardian.db
  |
  |-- Tabel: users            (whitelist, roles)
  |-- Tabel: audit_logs       (semua tindakan)
  |-- Tabel: scheduled_jobs   (cron jobs)
  |-- Tabel: alert_configs    (threshold konfigurasi)
  |-- Tabel: plugin_configs   (konfigurasi per plugin)
  |-- Tabel: sessions         (sesi aktif pengguna)
  |-- Tabel: migrations       (tracking migrasi)
```

---

## 7. Komponen Eksternal (External Components)

### 7.1 Telegram Bot API

- **URL:** https://api.telegram.org
- **Protokol:** HTTPS REST API
- **Mode koneksi:** Long Polling (default) atau Webhook (opsional)
- **Library:** python-telegram-bot v21+

### 7.2 Docker Engine

- **Koneksi:** Unix socket (`/var/run/docker.sock`)
- **Library:** docker-py (Docker SDK for Python)
- **Mode:** Hanya digunakan jika Docker terinstall

### 7.3 AI Provider (Opsional)

- **OpenAI API:** GPT-4o, GPT-4o-mini
- **Google Gemini API:** Gemini Pro
- **Ollama:** LLM lokal (self-hosted)
- **Mode:** Plug-and-play melalui AI Gateway

### 7.4 Cloudflare (Plugin Masa Depan)

- **API:** Cloudflare REST API v4
- **Kegunaan:** Kelola DNS record, pantau Cloudflare Tunnel

### 7.5 Google Drive (Plugin Masa Depan)

- **API:** Google Drive API v3
- **Kegunaan:** Backup file konfigurasi dan database

### 7.6 GitHub (Plugin Masa Depan)

- **API:** GitHub REST API v3 / GraphQL
- **Kegunaan:** Notifikasi CI/CD, trigger workflow

---

## 8. Alur Data (Data Flow)

### 8.1 Alur Command dari Pengguna

```
1. Pengguna ketik /docker list di Telegram
2. Telegram kirim Update object ke bot via long polling
3. BotGateway terima update dan parse command: "docker", args: ["list"]
4. AuthMiddleware:
   a. Cek user_id di tabel users
   b. Jika tidak ada -> kirim pesan "Akses Ditolak" -> STOP
   c. Jika ada -> ambil role user
5. RateLimitMiddleware:
   a. Cek hitungan command user dalam 1 menit terakhir
   b. Jika melebihi limit -> kirim pesan "Terlalu banyak perintah" -> STOP
6. AuditMiddleware:
   a. Catat command ke tabel audit_logs dengan status "received"
7. Router:
   a. Temukan handler untuk namespace "docker" dan command "list"
   b. Cek apakah role user memiliki izin untuk command ini
   c. Jika tidak izin -> kirim pesan "Tidak ada izin" -> STOP
8. DockerPlugin.handle_list():
   a. Panggil DockerService.get_containers()
   b. DockerService query Docker API via unix socket
   c. Terima list kontainer
9. MessageBuilder.build_container_list():
   a. Format data menjadi teks dengan emoji
   b. Buat InlineKeyboard untuk aksi per kontainer
10. BotGateway.send_message():
    a. Kirim pesan ke Telegram API
    b. Telegram deliver ke pengguna
11. AuditMiddleware update record: status "completed"
```

### 8.2 Alur Alert Otomatis

```
1. SchedulerEngine jalankan AlertLoop setiap 60 detik
2. AlertLoop panggil SystemService.get_metrics()
3. SystemService kembalikan: cpu=87%, ram=45%, disk=92%
4. AlertLoop bandingkan dengan konfigurasi threshold dari database
5. cpu_threshold=90% -> TIDAK trigger
6. disk_threshold=90% -> TRIGGER (92% > 90%)
7. NotificationService.send_alert():
   a. Query tabel users untuk mendapatkan alert_recipients
   b. Format pesan alert dengan detail disk usage
   c. BotGateway.send_message() ke setiap recipient
8. AlertLoop catat alert ke audit_logs
9. AlertLoop set cooldown (tidak kirim alert sama lagi dalam 30 menit)
```

---

## 9. Arsitektur Lapisan (Layered Architecture)

```
+------------------------------------------------------------------+
|                     PRESENTATION LAYER                           |
|  Bot Gateway | Message Builder | Keyboard Builder | Formatter    |
+------------------------------------------------------------------+
|                     APPLICATION LAYER                            |
|  Command Router | Plugin Manager | Auth Service | Scheduler      |
+------------------------------------------------------------------+
|                      DOMAIN LAYER                                |
|  Plugin Handlers | Business Rules | Alert Engine | RBAC Rules    |
+------------------------------------------------------------------+
|                    INFRASTRUCTURE LAYER                          |
|  Database Manager | System Service | Docker Service | AI Gateway |
+------------------------------------------------------------------+
|                      EXTERNAL LAYER                              |
|  Telegram API | Docker Engine | Linux OS | AI Provider | Cloud   |
+------------------------------------------------------------------+
```

**Aturan ketergantungan lapisan:**
- Lapisan atas boleh bergantung pada lapisan bawah.
- Lapisan bawah **tidak boleh** bergantung pada lapisan atas.
- Plugin berkomunikasi antar-plugin hanya melalui Event Bus, bukan direct import.

---

## 10. Arsitektur Deployment

```
VPS / Server Linux
+------------------------------------------------------------------+
|                                                                  |
|  OS: Debian 12 / Ubuntu 22.04+                                  |
|                                                                  |
|  User: serverinka (non-root, sudoers untuk operasi terbatas)    |
|                                                                  |
|  /opt/serverinka/guardian/      <- Kode aplikasi                |
|  /var/lib/serverinka/           <- Data (database, logs)        |
|  /etc/serverinka/               <- Konfigurasi (.env)           |
|                                                                  |
|  +------------------------------------+                          |
|  |  systemd                           |                          |
|  |                                    |                          |
|  |  serverinka-guardian.service       |                          |
|  |    -> ExecStart: python -m guardian|                          |
|  |    -> Restart: always              |                          |
|  |    -> RestartSec: 10               |                          |
|  |    -> User: serverinka             |                          |
|  |    -> EnvironmentFile: /etc/...    |                          |
|  +------------------------------------+                          |
|                                                                  |
|  +------------------------------------+                          |
|  |  Python Virtual Environment        |                          |
|  |  /opt/serverinka/guardian/.venv/  |                          |
|  |    -> Python 3.12+                 |                          |
|  |    -> All dependencies installed   |                          |
|  +------------------------------------+                          |
|                                                                  |
|  +------------------------------------+                          |
|  |  SQLite Database                   |                          |
|  |  /var/lib/serverinka/guardian.db  |                          |
|  |    -> WAL mode enabled             |                          |
|  |    -> Daily backup cron job        |                          |
|  +------------------------------------+                          |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 11. Keputusan Desain

### Mengapa Plugin-Based Monolith, bukan Microservices?

| Aspek | Plugin Monolith | Microservices |
|-------|-----------------|---------------|
| Kompleksitas operasional | Rendah | Tinggi |
| Latensi internal | Sangat rendah (function call) | Lebih tinggi (network) |
| Resource usage | Rendah (satu proses) | Tinggi (banyak proses) |
| Cocok untuk | 1 VPS, tim kecil | Ratusan server, tim besar |
| Deployment | Satu service | Orkestrasi kompleks |

Untuk target pengguna Serverinka Guardian (individu dan tim kecil), Plugin-Based Monolith adalah pilihan yang tepat.

### Mengapa Long Polling, bukan Webhook?

- Long polling lebih mudah dikonfigurasi (tidak butuh domain & SSL).
- Cocok untuk deployment di VPS tanpa domain publik.
- python-telegram-bot mendukung long polling dengan sangat baik.
- Webhook dapat diaktifkan sebagai opsi konfigurasi untuk pengguna advanced.

### Mengapa asyncio, bukan Threading?

- Operasi I/O-bound mendominasi (Telegram API, Docker API, sistem file).
- asyncio lebih efisien untuk I/O-bound workload dibandingkan threading.
- python-telegram-bot v20+ dan aiosqlite berjalan secara native dengan asyncio.
- Lebih mudah di-reason tentang konkurensi dengan async/await.

---

## 12. Checklist Implementasi

### Core Engine

- [ ] Implementasi ApplicationContext sebagai dependency container
- [ ] Implementasi graceful shutdown dengan penanganan sinyal OS
- [ ] Implementasi startup sequence dengan urutan yang benar
- [ ] Unit test untuk lifecycle engine

### Bot Gateway

- [ ] Implementasi long polling dengan auto-reconnect
- [ ] Implementasi middleware chain yang dapat dikonfigurasi
- [ ] Implementasi error handler global
- [ ] Unit test untuk routing dan middleware

### Plugin Manager

- [ ] Implementasi auto-discovery plugin dari folder plugins/
- [ ] Implementasi dependency resolution antar plugin
- [ ] Implementasi plugin lifecycle (load, activate, deactivate, unload)
- [ ] Unit test untuk plugin loading dan isolation

### Event Bus

- [ ] Implementasi async publish/subscribe
- [ ] Implementasi error isolation per subscriber
- [ ] Unit test untuk event delivery

### Database Manager

- [ ] Implementasi migration system
- [ ] Implementasi connection management untuk aiosqlite
- [ ] Semua tabel dari 04_DATABASE_DESIGN.md diimplementasi
- [ ] Unit test dengan database in-memory

---

*Referensi: [01_PRD.md](01_PRD.md) | [03_TECH_STACK.md](03_TECH_STACK.md) | [04_DATABASE_DESIGN.md](04_DATABASE_DESIGN.md) | [07_PLUGIN_SYSTEM.md](07_PLUGIN_SYSTEM.md)*
