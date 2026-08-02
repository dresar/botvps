# Serverinka Guardian

<div align="center">

🤖 **Bot Telegram open source sebagai pusat kendali VPS Linux dan server pribadi**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

</div>

---

## ✨ Fitur Utama

- 📊 **Monitor Server** — CPU, RAM, Disk, Network, proses secara real-time
- ⚙️ **Manajemen Layanan** — Start/stop/restart layanan systemd
- 🐳 **Manajemen Docker** — Kelola kontainer dan image Docker
- 🔔 **Alert Otomatis** — Notifikasi saat metrik melewati threshold
- 📅 **Penjadwalan** — Tugas terjadwal berbasis cron expression
- 🔐 **RBAC** — Role-based access control (super_admin, admin, operator, viewer)
- 📋 **Audit Log** — Semua tindakan tercatat
- 🔌 **Plugin System** — Dapat diperluas tanpa mengubah kode inti

## 🖥️ Target Sistem

| OS | Versi | Status |
|----|-------|--------|
| Debian | 12 (Bookworm) | ✅ Primary |
| Ubuntu Server | 22.04 LTS | ✅ Supported |
| Ubuntu Server | 24.04 LTS | ✅ Supported |

## 🚀 Instalasi Cepat

### 1. Prasyarat

```bash
# Pastikan Python 3.12+ tersedia
python3 --version

# Install uv (package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone & Konfigurasi

```bash
git clone https://github.com/your-username/serverinka-guardian.git
cd serverinka-guardian

# Salin template konfigurasi
cp .env.example .env

# Edit konfigurasi (isi TELEGRAM_BOT_TOKEN dan TELEGRAM_ADMIN_USER_IDS)
nano .env
```

### 3. Install Dependencies & Jalankan

```bash
# Install semua dependency
uv sync

# Jalankan bot
uv run python -m guardian
```

### 4. Deployment Production (Debian/Ubuntu)

```bash
# Jalankan setup script otomatis
sudo bash scripts/setup.sh
```

Script ini akan:
- Membuat user `serverinka` (non-root)
- Menginstall semua dependencies
- Mengkonfigurasi systemd service
- Mengatur sudo rules yang diperlukan

## ⚙️ Konfigurasi

Semua konfigurasi menggunakan file `.env`. Lihat [`.env.example`](.env.example) untuk daftar lengkap variabel yang tersedia.

Variabel wajib:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_ADMIN_USER_IDS=your_telegram_user_id
```

## 🔧 Perintah Bot

| Command | Deskripsi | Role |
|---------|-----------|------|
| `/start` | Tampilkan menu utama | Semua |
| `/status` | Dashboard server | Semua |
| `/service list` | Daftar layanan | Viewer+ |
| `/docker list` | Daftar kontainer | Viewer+ |
| `/alert list` | Konfigurasi alert | Viewer+ |
| `/user list` | Manajemen pengguna | Admin+ |
| `/audit` | Audit log | Admin+ |
| `/system reboot` | Reboot server | Admin+ |

## 🏗️ Arsitektur

```
guardian/
├── core/          # Core engine (config, auth, db, scheduler, plugin manager)
├── interfaces/    # Abstract classes (BasePlugin, BaseService, BaseRepository)
├── utils/         # Utilities (formatters, validators, sandbox, message builder)
├── migrations/    # Database migrations
└── plugins/       # Plugin modules
    ├── system/         # System monitoring
    ├── service_manager/ # systemd management
    ├── docker/         # Docker management
    ├── notification/   # Alert system
    ├── scheduler_ui/   # Job scheduler
    ├── user_manager/   # User management
    └── audit_viewer/   # Audit log viewer
```

Lihat folder [`docs/`](docs/) untuk dokumentasi teknis lengkap (10 dokumen).

## 🔌 Membuat Plugin

Lihat [07_PLUGIN_SYSTEM.md](docs/07_PLUGIN_SYSTEM.md) dan [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan lengkap.

```
guardian/plugins/my_plugin/
├── __init__.py
├── plugin.py      # class MyPlugin(BasePlugin)
├── handlers.py    # Command handlers
├── service.py     # Business logic
└── messages.py    # Message templates
```

## 🧪 Development

```bash
# Install dev dependencies
uv sync --extra dev

# Jalankan test
uv run pytest

# Linting
uv run ruff check .

# Type checking
uv run mypy .
```

## 📄 Lisensi

[MIT License](LICENSE) — bebas digunakan, dimodifikasi, dan didistribusikan.

## 🤝 Kontribusi

Lihat [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan kontribusi.
