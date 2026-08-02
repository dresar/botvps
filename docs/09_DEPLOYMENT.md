# 09 — Panduan Deployment
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [03_TECH_STACK.md](03_TECH_STACK.md) | [06_SECURITY.md](06_SECURITY.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Persyaratan Sistem](#2-persyaratan-sistem)
3. [Struktur Folder Proyek Lengkap](#3-struktur-folder-proyek-lengkap)
4. [Proses Instalasi (Fresh VPS)](#4-proses-instalasi-fresh-vps)
5. [Konfigurasi Lingkungan (.env)](#5-konfigurasi-lingkungan-env)
6. [Konfigurasi systemd Service](#6-konfigurasi-systemd-service)
7. [Manajemen Virtual Environment](#7-manajemen-virtual-environment)
8. [Strategi Backup](#8-strategi-backup)
9. [Strategi Restore](#9-strategi-restore)
10. [Strategi Update](#10-strategi-update)
11. [Strategi Rollback](#11-strategi-rollback)
12. [Monitoring & Observability](#12-monitoring--observability)
13. [Logging Management](#13-logging-management)
14. [CI/CD Readiness](#14-cicd-readiness)
15. [Development Environment](#15-development-environment)
16. [Troubleshooting Umum](#16-troubleshooting-umum)
17. [Keputusan Desain](#17-keputusan-desain)
18. [Checklist Implementasi](#18-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini menjelaskan seluruh proses deployment Serverinka Guardian dari tahap development hingga production. Mencakup instalasi, konfigurasi, monitoring, backup, update, dan rollback. Tujuannya adalah memastikan deployment yang repeatable, aman, dan mudah dipahami.

---

## 2. Persyaratan Sistem

### 2.1 Persyaratan Minimum (Production)

| Komponen | Minimum | Rekomendasi |
|----------|---------|-------------|
| OS | Debian 12 / Ubuntu 22.04 | Debian 12 (Bookworm) |
| CPU | 1 vCPU | 2 vCPU |
| RAM | 512 MB (bot only) | 1 GB |
| Disk | 2 GB | 10 GB |
| Python | 3.12+ | 3.12.x |
| Koneksi Internet | Wajib | Stabil |

### 2.2 Software Dependencies

```
Sistem (apt):
  - python3.12
  - python3.12-venv
  - python3.12-dev
  - git
  - curl
  - sqlite3

Opsional (untuk fitur Docker):
  - docker-ce
  - docker-compose-plugin
```

### 2.3 OS yang Didukung

| OS | Versi | Status |
|----|-------|--------|
| Debian | 12 (Bookworm) | PRIMARY |
| Ubuntu Server | 22.04 LTS | SUPPORTED |
| Ubuntu Server | 24.04 LTS | SUPPORTED |
| Debian | 11 (Bullseye) | NOT SUPPORTED (Python 3.11) |

---

## 3. Struktur Folder Proyek Lengkap

### 3.1 Repositori (Development)

```
serverinka-guardian/             <- Root repositori
|
|-- guardian/                    <- Package Python utama
|   |-- __init__.py
|   |-- __main__.py
|   |-- core/
|   |-- interfaces/
|   |-- utils/
|   |-- plugins/
|   `-- migrations/
|
|-- tests/
|-- docs/                        <- 10 dokumen ini
|-- scripts/
|   |-- setup.sh                 <- Script instalasi production
|   |-- update.sh                <- Script update
|   |-- backup.sh                <- Script backup manual
|   |-- restore.sh               <- Script restore
|   `-- dev.sh                   <- Setup development environment
|
|-- pyproject.toml
|-- uv.lock
|-- .python-version
|-- .env.example
|-- .gitignore
|-- README.md
|-- CONTRIBUTING.md
|-- CHANGELOG.md
`-- LICENSE
```

### 3.2 Struktur di VPS (Production)

```
/opt/serverinka/
  guardian/                      <- Kode aplikasi (git clone di sini)
    .venv/                       <- Python virtual environment
    guardian/                    <- Package Python
    scripts/
    pyproject.toml
    ...

/etc/serverinka/
  guardian.env                   <- Konfigurasi production (mode 600)

/var/lib/serverinka/
  guardian.db                    <- Database SQLite
  backups/                       <- Backup database
    guardian_20260801.db.gz
    guardian_20260802.db.gz
    ...

/var/log/serverinka/
  guardian.log                   <- Log file (opsional)

/etc/systemd/system/
  serverinka-guardian.service    <- systemd service definition

/etc/sudoers.d/
  serverinka                     <- Sudo rules untuk user serverinka
```

---

## 4. Proses Instalasi (Fresh VPS)

### 4.1 Alur Instalasi Otomatis (setup.sh)

```
Prasyarat sebelum menjalankan setup.sh:
  1. VPS dengan Debian 12 atau Ubuntu 22.04+
  2. Akses root atau sudo
  3. Koneksi internet
  4. Bot token dari @BotFather
  5. Telegram User ID super admin

Perintah instalasi:
  curl -fsSL https://raw.githubusercontent.com/user/serverinka-guardian/main/scripts/setup.sh | bash
  
  ATAU clone manual:
  git clone https://github.com/user/serverinka-guardian.git
  cd serverinka-guardian
  sudo bash scripts/setup.sh
```

### 4.2 Langkah-langkah setup.sh

```
STEP 1: Verifikasi OS
  - Cek versi OS (Debian 12 atau Ubuntu 22.04+)
  - Jika tidak didukung: tampilkan error dan keluar

STEP 2: Install Dependencies Sistem
  apt-get update
  apt-get install -y python3.12 python3.12-venv python3.12-dev git curl sqlite3

STEP 3: Install uv (Python Package Manager)
  curl -LsSf https://astral.sh/uv/install.sh | sh

STEP 4: Buat User Serverinka
  useradd --system --no-create-home --shell /bin/false serverinka
  
STEP 5: Setup Direktori
  mkdir -p /opt/serverinka
  mkdir -p /var/lib/serverinka/backups
  mkdir -p /var/log/serverinka
  mkdir -p /etc/serverinka
  
STEP 6: Clone / Copy Kode
  cp -r . /opt/serverinka/guardian
  chown -R serverinka:serverinka /opt/serverinka/guardian

STEP 7: Install Python Dependencies
  cd /opt/serverinka/guardian
  sudo -u serverinka uv sync --frozen
  
STEP 8: Konfigurasi .env
  Tanya interaktif:
    - TELEGRAM_BOT_TOKEN
    - TELEGRAM_ADMIN_USER_IDS
    - DATABASE_PATH (default: /var/lib/serverinka/guardian.db)
  Simpan ke /etc/serverinka/guardian.env
  chmod 600 /etc/serverinka/guardian.env
  chown serverinka:serverinka /etc/serverinka/guardian.env

STEP 9: Setup sudo Rules
  cp scripts/sudoers.d/serverinka /etc/sudoers.d/serverinka
  chmod 440 /etc/sudoers.d/serverinka
  
STEP 10: Inisialisasi Database
  sudo -u serverinka uv run python -m guardian db:migrate

STEP 11: Install systemd Service
  cp scripts/serverinka-guardian.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable serverinka-guardian
  systemctl start serverinka-guardian

STEP 12: Verifikasi
  systemctl status serverinka-guardian
  journalctl -u serverinka-guardian -n 20

SELESAI: Tampilkan informasi penting ke user
  - Status bot
  - Perintah manajemen
  - Lokasi file konfigurasi
  - Cara melihat log
```

---

## 5. Konfigurasi Lingkungan (.env)

### 5.1 File .env.example (Lengkap)

```
# =====================================================================
# SERVERINKA GUARDIAN — KONFIGURASI
# Salin file ini ke /etc/serverinka/guardian.env dan isi nilainya.
# JANGAN commit file .env ke version control!
# =====================================================================

# ---- TELEGRAM --------------------------------------------------------
# Token bot dari @BotFather (WAJIB)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Telegram User ID super admin, pisahkan dengan koma jika lebih dari satu (WAJIB)
TELEGRAM_ADMIN_USER_IDS=123456789,987654321

# Mode koneksi Telegram: polling (default) atau webhook
TELEGRAM_MODE=polling

# Konfigurasi webhook (hanya jika TELEGRAM_MODE=webhook)
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
TELEGRAM_WEBHOOK_PORT=8443
TELEGRAM_WEBHOOK_SECRET=random_secret_string

# ---- DATABASE --------------------------------------------------------
# Path ke file database SQLite
DATABASE_PATH=/var/lib/serverinka/guardian.db

# ---- LOGGING ---------------------------------------------------------
# Level log: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Path ke file log (kosongkan untuk hanya ke stdout/journald)
LOG_FILE_PATH=

# ---- SCHEDULER -------------------------------------------------------
# Interval pengecekan alert dalam detik (default: 60)
SCHEDULER_ALERT_INTERVAL_SECONDS=60

# ---- RATE LIMITING ---------------------------------------------------
# Maksimal perintah per window per user (default: 30)
RATE_LIMIT_COMMANDS_PER_WINDOW=30

# Durasi window dalam detik (default: 60)
RATE_LIMIT_WINDOW_SECONDS=60

# ---- DOCKER ----------------------------------------------------------
# Aktifkan integrasi Docker (true/false)
DOCKER_ENABLED=true

# ---- AI INTEGRATION --------------------------------------------------
# Provider AI: disabled, openai, gemini, ollama (default: disabled)
AI_PROVIDER=disabled

# API key untuk provider AI yang dipilih
AI_API_KEY=

# Model AI yang digunakan
AI_MODEL=gpt-4o-mini

# URL untuk Ollama (jika provider=ollama)
OLLAMA_BASE_URL=http://localhost:11434

# ---- BACKUP ----------------------------------------------------------
# Aktifkan backup otomatis (true/false)
BACKUP_ENABLED=true

# Jumlah hari retensi backup (default: 7)
BACKUP_RETENTION_DAYS=7

# Path ke folder backup
BACKUP_PATH=/var/lib/serverinka/backups

# ---- AUDIT LOG -------------------------------------------------------
# Jumlah hari retensi audit log (default: 90)
AUDIT_LOG_RETENTION_DAYS=90

# ---- PLUGINS ---------------------------------------------------------
# Plugin yang dinonaktifkan, pisahkan dengan koma (kosong = semua aktif)
DISABLED_PLUGINS=

# ---- ADVANCED --------------------------------------------------------
# Token timeout untuk koneksi Telegram API (detik)
CONNECT_TIMEOUT=10
READ_TIMEOUT=10
WRITE_TIMEOUT=10
POOL_TIMEOUT=10
```

---

## 6. Konfigurasi systemd Service

### 6.1 serverinka-guardian.service

```
[Unit]
Description=Serverinka Guardian - Telegram VPS Control Bot
Documentation=https://github.com/user/serverinka-guardian
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=serverinka
Group=serverinka

WorkingDirectory=/opt/serverinka/guardian
ExecStart=/opt/serverinka/guardian/.venv/bin/python -m guardian
ExecReload=/bin/kill -HUP $MAINPID

EnvironmentFile=/etc/serverinka/guardian.env

# Restart behavior
Restart=always
RestartSec=10
TimeoutStopSec=30

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/serverinka /var/log/serverinka
CapabilityBoundingSet=

# Resource limits
LimitNOFILE=65535
MemoryMax=256M

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=serverinka-guardian

[Install]
WantedBy=multi-user.target
```

### 6.2 Perintah Manajemen Service

```
Start bot:    sudo systemctl start serverinka-guardian
Stop bot:     sudo systemctl stop serverinka-guardian
Restart bot:  sudo systemctl restart serverinka-guardian
Status bot:   sudo systemctl status serverinka-guardian
Enable bot:   sudo systemctl enable serverinka-guardian
Disable bot:  sudo systemctl disable serverinka-guardian

Lihat log:    sudo journalctl -u serverinka-guardian -f
Log N baris:  sudo journalctl -u serverinka-guardian -n 100
Log hari ini: sudo journalctl -u serverinka-guardian --since today
```

---

## 7. Manajemen Virtual Environment

### 7.1 Setup Virtual Environment dengan uv

```
cd /opt/serverinka/guardian

# Install semua dependency dari lockfile (reproducible)
uv sync --frozen

# Install termasuk dev dependencies (untuk development)
uv sync --frozen --extra dev

# Tambah dependency baru (hanya untuk developer)
uv add nama_package

# Update lockfile setelah tambah dependency
uv lock
```

### 7.2 Lokasi Virtual Environment

```
/opt/serverinka/guardian/.venv/
  bin/
    python         <- Python 3.12 interpreter
    python3
    python3.12
    pip
    ...
  lib/
    python3.12/
      site-packages/  <- Semua package terinstall
  ...
```

### 7.3 Menjalankan Perintah dalam venv

```
# Cara 1: uv run (rekomendasi)
cd /opt/serverinka/guardian
uv run python -m guardian

# Cara 2: Aktifkan venv manual
source /opt/serverinka/guardian/.venv/bin/activate
python -m guardian
deactivate

# Cara 3: Path langsung ke interpreter
/opt/serverinka/guardian/.venv/bin/python -m guardian
```

---

## 8. Strategi Backup

### 8.1 Jenis Backup

| Jenis | Frekuensi | Retensi | Target |
|-------|-----------|---------|--------|
| Database SQLite | Harian (02:00 UTC) | 7 hari | /var/lib/serverinka/backups/ |
| File konfigurasi | Harian (02:00 UTC) | 7 hari | /var/lib/serverinka/backups/ |
| Kode aplikasi | Saat update | via git | GitHub repository |

### 8.2 Proses Backup Otomatis

Backup dilakukan oleh scheduled job internal bot setiap hari pukul 02:00 UTC.

```
Proses backup harian:
  1. Bot menjalankan backup job dari scheduler
  2. Jalankan: sqlite3 /var/lib/serverinka/guardian.db ".backup '/var/lib/serverinka/backups/guardian_YYYYMMDD.db'"
  3. Compress: gzip -9 /var/lib/serverinka/backups/guardian_YYYYMMDD.db
  4. Hapus backup yang lebih lama dari BACKUP_RETENTION_DAYS
  5. Catat hasil backup di audit log
  6. Opsional: upload ke cloud storage (jika plugin dikonfigurasi)
```

### 8.3 Backup Manual via Skrip

```
sudo -u serverinka bash /opt/serverinka/guardian/scripts/backup.sh

Script ini:
  - Buat backup database dengan timestamp
  - Buat backup file konfigurasi (tanpa nilai sensitif)
  - Tampilkan lokasi backup yang dibuat
```

### 8.4 Backup via Bot

```
Admin kirim perintah: /backup now
Bot membuat backup segera
Bot kirim konfirmasi dengan lokasi dan ukuran file backup
Opsional: Bot kirim file backup via Telegram (jika < 50MB)
```

---

## 9. Strategi Restore

### 9.1 Restore Database

```
STEP 1: Stop bot
  sudo systemctl stop serverinka-guardian

STEP 2: Backup database saat ini (precaution)
  sudo -u serverinka cp /var/lib/serverinka/guardian.db /var/lib/serverinka/guardian.db.before_restore

STEP 3: Pilih file backup yang akan di-restore
  ls -la /var/lib/serverinka/backups/

STEP 4: Restore
  sudo -u serverinka gunzip -c /var/lib/serverinka/backups/guardian_YYYYMMDD.db.gz > /var/lib/serverinka/guardian.db

STEP 5: Verifikasi integritas
  sqlite3 /var/lib/serverinka/guardian.db "PRAGMA integrity_check;"
  
STEP 6: Jalankan migrasi (jika perlu)
  cd /opt/serverinka/guardian
  sudo -u serverinka uv run python -m guardian db:migrate

STEP 7: Start bot
  sudo systemctl start serverinka-guardian

STEP 8: Verifikasi bot berjalan normal
  sudo systemctl status serverinka-guardian
```

### 9.2 Restore Full (Disaster Recovery)

Jika server perlu di-reinstall dari nol:

```
1. Setup VPS baru dengan OS yang sama
2. Clone repositori
3. Jalankan setup.sh
4. Ganti database dengan backup: step 4-6 di atas
5. Pastikan .env dikonfigurasi dengan nilai yang sama
6. Verifikasi bot berjalan
```

---

## 10. Strategi Update

### 10.1 Update Bot ke Versi Terbaru

```
Cara 1: Menggunakan script update.sh
  sudo bash /opt/serverinka/guardian/scripts/update.sh

Cara 2: Manual
  1. Buat backup database:
     sudo -u serverinka bash /opt/serverinka/guardian/scripts/backup.sh
  
  2. Pull perubahan terbaru:
     cd /opt/serverinka/guardian
     sudo -u serverinka git pull origin main
  
  3. Update dependencies:
     sudo -u serverinka uv sync --frozen
  
  4. Jalankan migrasi database:
     sudo -u serverinka uv run python -m guardian db:migrate
  
  5. Restart bot:
     sudo systemctl restart serverinka-guardian
  
  6. Verifikasi:
     sudo systemctl status serverinka-guardian
     sudo journalctl -u serverinka-guardian -n 20
```

### 10.2 Update via Bot (Masa Depan)

Fitur update dari dalam bot direncanakan untuk versi 1.1:
```
/system update-bot    -> Admin dapat trigger update langsung dari Telegram
```

---

## 11. Strategi Rollback

### 11.1 Rollback Kode

```
Jika update bermasalah, rollback ke versi sebelumnya:

  cd /opt/serverinka/guardian

  # Lihat daftar commit
  git log --oneline -10

  # Rollback ke commit tertentu
  sudo -u serverinka git reset --hard <commit_hash>
  
  # Atau rollback ke tag versi tertentu
  sudo -u serverinka git checkout v1.0.0

  # Update dependencies ke versi yang sesuai
  sudo -u serverinka uv sync --frozen

  # Restart bot
  sudo systemctl restart serverinka-guardian
```

### 11.2 Rollback Database

Jika migrasi database bermasalah:

```
1. Stop bot: sudo systemctl stop serverinka-guardian
2. Restore backup dari sebelum update
3. Rollback kode
4. Start bot: sudo systemctl start serverinka-guardian
```

### 11.3 Blue-Green Deployment (Masa Depan)

Untuk deployment tanpa downtime, rencanakan menggunakan dua folder:
- `/opt/serverinka/guardian_blue/` — Versi lama (aktif)
- `/opt/serverinka/guardian_green/` — Versi baru (testing)

Switch dengan mengubah symlink `/opt/serverinka/guardian -> guardian_blue/green`.

---

## 12. Monitoring & Observability

### 12.1 Health Check Endpoint

Bot menyediakan health check yang dapat dipantau oleh monitoring eksternal:

```
Cara 1: systemd status
  systemctl is-active serverinka-guardian
  -> Kembalikan 0 jika aktif, non-zero jika tidak

Cara 2: Process check
  pgrep -f "python -m guardian"

Cara 3: Database check (bot harus bisa query database)
  sqlite3 /var/lib/serverinka/guardian.db "SELECT 1;"

Cara 4: Ping Telegram (masa depan)
  Bot dapat didaftarkan ke UptimeRobot atau Uptime-Kuma
  dengan test pesan ke diri sendiri setiap X menit
```

### 12.2 Metrics yang Dipantau

```
Bot Metrics:
  - Status proses (running/stopped)
  - Uptime bot
  - Jumlah command diproses per jam
  - Jumlah error per jam
  - Latency rata-rata per command

System Metrics (oleh bot sendiri):
  - CPU usage
  - RAM usage
  - Disk usage
  - Layanan kritis status
  - Docker container status
```

### 12.3 Alert Rules Default

```
Alert yang aktif secara default saat instalasi:
  - CPU > 90% selama 5 menit berturut-turut
  - RAM > 90%
  - Disk / > 90%
  - Layanan dalam SYSTEM_WATCHED_SERVICES gagal
```

---

## 13. Logging Management

### 13.1 Log Destination

```
Production (systemd):
  stdout/stderr -> journald
  Query: journalctl -u serverinka-guardian

Optional file log:
  /var/log/serverinka/guardian.log
  Dikonfigurasi via LOG_FILE_PATH di .env
```

### 13.2 Log Rotation

```
Jika menggunakan file log, tambahkan logrotate config:
  /etc/logrotate.d/serverinka-guardian:
  
  /var/log/serverinka/guardian.log {
      daily
      rotate 30
      compress
      delaycompress
      missingok
      notifempty
      postrotate
          systemctl kill -s HUP serverinka-guardian.service
      endscript
  }
```

### 13.3 journald Configuration

```
Atur retensi log systemd di /etc/systemd/journald.conf:
  SystemMaxUse=500M
  SystemKeepFree=1G
  MaxRetentionSec=30day
```

---

## 14. CI/CD Readiness

### 14.1 GitHub Actions Workflow

File: `.github/workflows/ci.yml`

```
Trigger: push ke main, pull_request ke main

Jobs:
  lint:
    - uv run ruff check .
    - uv run mypy .

  test:
    - uv run pytest --cov=guardian --cov-report=xml
    - Upload coverage report

  security:
    - uv run pip-audit (atau safety check)
    
  build-check:
    - Verifikasi uv sync --frozen berhasil
    - Verifikasi aplikasi dapat distart (dry-run)
```

### 14.2 Release Workflow

File: `.github/workflows/release.yml`

```
Trigger: push tag dengan format v*.*.*

Jobs:
  release:
    - Buat GitHub Release
    - Upload CHANGELOG
    - Beri tag ke repositori
```

### 14.3 Deployment Otomatis (Opsional)

Untuk deployment otomatis ke VPS saat release:

```
Jobs:
  deploy:
    needs: release
    - SSH ke VPS
    - Jalankan update.sh
    - Verifikasi bot aktif
    - Kirim notifikasi Telegram ke admin
```

---

## 15. Development Environment

### 15.1 Setup Dev Environment (Lokal)

```
PRASYARAT:
  - Python 3.12+ terinstall
  - uv terinstall
  - git

LANGKAH:
  1. Clone repositori:
     git clone https://github.com/user/serverinka-guardian.git
     cd serverinka-guardian

  2. Install dependencies:
     uv sync --extra dev

  3. Salin file konfigurasi:
     cp .env.example .env
     # Edit .env dengan nilai development

  4. Setup pre-commit hooks (opsional tapi direkomendasikan):
     uv run pre-commit install

  5. Jalankan bot dalam mode dev:
     uv run python -m guardian

  6. Jalankan test:
     uv run pytest

  7. Jalankan linting:
     uv run ruff check .
     uv run mypy .
```

### 15.2 Konfigurasi .env untuk Development

```
TELEGRAM_BOT_TOKEN=dev_bot_token
TELEGRAM_ADMIN_USER_IDS=your_telegram_id
DATABASE_PATH=./dev_guardian.db
LOG_LEVEL=DEBUG
DOCKER_ENABLED=true
AI_PROVIDER=disabled
BACKUP_ENABLED=false
RATE_LIMIT_COMMANDS_PER_WINDOW=100
```

### 15.3 Running Tests

```
Jalankan semua test:
  uv run pytest

Jalankan dengan coverage:
  uv run pytest --cov=guardian --cov-report=html

Jalankan test tertentu:
  uv run pytest tests/unit/core/test_auth.py

Jalankan dengan verbose:
  uv run pytest -v

Jalankan hanya test yang gagal terakhir:
  uv run pytest --lf
```

---

## 16. Troubleshooting Umum

### 16.1 Bot Tidak Merespons

```
Diagnosis:
  1. sudo systemctl status serverinka-guardian
  2. sudo journalctl -u serverinka-guardian -n 50

Kemungkinan penyebab:
  a. Bot token salah -> periksa /etc/serverinka/guardian.env
  b. Tidak ada koneksi internet -> ping api.telegram.org
  c. Bot crash saat startup -> lihat log untuk stack trace
  d. Dependency tidak terinstall -> cd /opt/... && uv sync --frozen
```

### 16.2 "Permission Denied" saat Menjalankan Command

```
Diagnosis:
  sudo -l -U serverinka  (lihat sudo permissions yang ada)

Kemungkinan penyebab:
  - /etc/sudoers.d/serverinka tidak dikonfigurasi dengan benar
  - Syntax error di file sudoers

Fix:
  sudo visudo -f /etc/sudoers.d/serverinka
```

### 16.3 Database Locked Error

```
Diagnosis:
  journalctl -u serverinka-guardian | grep "database is locked"

Kemungkinan penyebab:
  - Bot berjalan lebih dari satu instance
  - Proses crash yang meninggalkan lock

Fix:
  sudo systemctl stop serverinka-guardian
  sqlite3 /var/lib/serverinka/guardian.db "PRAGMA wal_checkpoint;"
  sudo systemctl start serverinka-guardian
```

### 16.4 Docker Plugin Tidak Berfungsi

```
Diagnosis:
  docker info  (jalankan sebagai user serverinka)
  ls -la /var/run/docker.sock

Kemungkinan penyebab:
  - User serverinka tidak dalam group docker
  - Docker daemon tidak berjalan

Fix:
  sudo usermod -aG docker serverinka
  sudo systemctl restart docker
  sudo systemctl restart serverinka-guardian
```

---

## 17. Keputusan Desain

### Mengapa Instalasi via Script, Bukan Package Manager?

Script instalasi lebih fleksibel dan tidak memerlukan repositori package khusus. Untuk proyek open source yang ingin mudah diinstall di berbagai VPS, script bash adalah pilihan yang praktis dan transparan (pengguna dapat membaca apa yang dilakukan).

### Mengapa /opt/serverinka, Bukan /home?

`/opt` adalah lokasi standar FHS (Filesystem Hierarchy Standard) untuk software add-on. Menggunakan `/opt` menghindari konflik dengan user home directories dan lebih mudah di-manage dengan permission yang tepat.

### Mengapa Database di /var/lib?

`/var/lib` adalah lokasi standar FHS untuk data variabel yang persisten. Memisahkan data dari kode memudahkan update kode tanpa kehilangan data, dan memudahkan backup hanya folder `/var/lib/serverinka`.

### Mengapa systemd RestartSec=10?

10 detik memberikan waktu yang cukup untuk pemulihan dari crash sementara (misalnya, koneksi jaringan terputus sementara), tanpa terlalu lama membuat bot tidak merespons.

---

## 18. Checklist Implementasi

### Script Instalasi

- [ ] `setup.sh` berjalan tanpa error di Debian 12 fresh install
- [ ] `setup.sh` berjalan tanpa error di Ubuntu 22.04 fresh install
- [ ] Semua direktori dibuat dengan permission yang benar
- [ ] User `serverinka` dibuat dengan benar
- [ ] sudo rules dikonfigurasi dengan benar
- [ ] systemd service diinstall dan berjalan otomatis

### Konfigurasi

- [ ] File `.env.example` berisi semua variabel yang diperlukan dengan dokumentasi
- [ ] Validasi semua variabel wajib saat startup
- [ ] Pesan error yang jelas jika variabel wajib tidak ada

### Backup & Restore

- [ ] Backup job terjadwal berjalan setiap hari
- [ ] Cleanup backup lama berjalan
- [ ] Script restore diuji dan berfungsi
- [ ] Prosedur disaster recovery didokumentasikan

### Update & Rollback

- [ ] `update.sh` berjalan tanpa error
- [ ] Prosedur rollback manual didokumentasikan
- [ ] Database migrasi dijalankan otomatis saat update

### CI/CD

- [ ] GitHub Actions workflow untuk linting dan testing dibuat
- [ ] Semua test lulus di CI
- [ ] Coverage report dikirim ke platform coverage (misal Codecov)

---

*Referensi: [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [03_TECH_STACK.md](03_TECH_STACK.md) | [06_SECURITY.md](06_SECURITY.md) | [10_DEVELOPMENT_RULES.md](10_DEVELOPMENT_RULES.md)*
