# 01 — Product Requirement Document (PRD)
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Visi Proyek](#2-visi-proyek)
3. [Tujuan Produk](#3-tujuan-produk)
4. [Target Pengguna](#4-target-pengguna)
5. [Ruang Lingkup Proyek](#5-ruang-lingkup-proyek)
6. [Fitur Versi Pertama (MVP)](#6-fitur-versi-pertama-mvp)
7. [Fitur Masa Depan](#7-fitur-masa-depan)
8. [User Journey](#8-user-journey)
9. [Use Case Utama](#9-use-case-utama)
10. [Non-Functional Requirement](#10-non-functional-requirement)
11. [Batasan Sistem](#11-batasan-sistem)
12. [Roadmap Pengembangan](#12-roadmap-pengembangan)
13. [Keputusan Desain](#13-keputusan-desain)
14. [Checklist Implementasi](#14-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini merupakan **sumber kebenaran tunggal (single source of truth)** untuk seluruh kebutuhan produk Serverinka Guardian. Semua keputusan implementasi, desain, dan arsitektur harus merujuk kembali ke dokumen ini.

Dokumen ini dibuat untuk:
- Mendefinisikan visi dan tujuan produk secara jelas dan terukur.
- Memberikan panduan bagi seluruh tim pengembang tentang apa yang dibangun dan mengapa.
- Menjadi referensi bagi kontributor open source.
- Memastikan konsistensi antara fitur, arsitektur, dan implementasi.

---

## 2. Visi Proyek

**Serverinka Guardian** adalah bot Telegram open source yang menjadi pusat kendali terpadu (*unified control plane*) untuk VPS Linux dan server pribadi.

### Pernyataan Visi

> *"Memberikan kendali penuh atas infrastruktur server kepada individu dan tim kecil melalui antarmuka percakapan Telegram yang aman, responsif, dan dapat diperluas."*

### Nilai Inti

| Nilai | Deskripsi |
|-------|-----------|
| **Keamanan** | Keamanan bukan fitur tambahan, melainkan fondasi arsitektur. |
| **Kemudahan** | Perintah kompleks dieksekusi melalui percakapan sederhana. |
| **Skalabilitas** | Dari satu VPS hingga kluster server tanpa perubahan kode inti. |
| **Keterbukaan** | Seluruh kode terbuka, dapat diaudit, dan dapat dikontribusi. |
| **Keandalan** | Bot harus tersedia 24/7 dengan recovery otomatis. |

---

## 3. Tujuan Produk

### Tujuan Bisnis

1. Menyediakan alternatif gratis dan open source untuk panel kontrol VPS komersial.
2. Mengurangi ketergantungan pada antarmuka web yang memerlukan akses browser.
3. Memungkinkan manajemen server dari perangkat mobile melalui Telegram.

### Tujuan Teknis

1. Membangun fondasi bot yang dapat dikembangkan selama bertahun-tahun tanpa refaktor besar.
2. Menyediakan sistem plugin yang memungkinkan komunitas menambah fungsionalitas.
3. Mengintegrasikan kemampuan AI untuk analisis log dan saran tindakan.
4. Memastikan seluruh operasi server dapat dilakukan tanpa mengakses SSH langsung.

### Metrik Keberhasilan (KPI)

| Metrik | Target v1.0 | Target v2.0 |
|--------|-------------|-------------|
| Waktu respons perintah | < 2 detik | < 1 detik |
| Uptime bot | > 99% | > 99.9% |
| Plugin aktif komunitas | 5 | 25+ |
| Command coverage dasar | 30 command | 100+ command |
| Waktu setup dari nol | < 15 menit | < 5 menit |

---

## 4. Target Pengguna

### Segmen Utama

#### 4.1 Developer Individual

- **Profil:** Developer yang mengelola satu atau beberapa VPS untuk proyek pribadi.
- **Kebutuhan:** Monitoring cepat, restart layanan, cek log tanpa buka terminal.
- **Tingkat Teknis:** Menengah hingga Tinggi.
- **Pain Point:** Harus membuka SSH dari berbagai perangkat untuk operasi rutin.

#### 4.2 Tim Engineering Kecil (2-15 orang)

- **Profil:** Tim startup atau agensi yang berbagi server atau infrastruktur.
- **Kebutuhan:** RBAC (Role-Based Access Control), audit log, notifikasi deployment.
- **Tingkat Teknis:** Menengah.
- **Pain Point:** Tidak ada satu titik kontrol yang aman untuk seluruh tim.

#### 4.3 Homelabber / Self-Hoster

- **Profil:** Penggemar teknologi yang menjalankan server rumah dengan CasaOS, Nextcloud, Jellyfin, dll.
- **Kebutuhan:** Manajemen kontainer Docker, cek status layanan, update sistem.
- **Tingkat Teknis:** Menengah.
- **Pain Point:** Ingin mengontrol homelab dari smartphone tanpa konfigurasi VPN kompleks.

#### 4.4 DevOps Engineer

- **Profil:** Engineer yang mengelola infrastruktur dan ingin alat bantu monitoring berbasis chat.
- **Kebutuhan:** Integrasi CI/CD, alert otomatis, laporan performa server.
- **Tingkat Teknis:** Tinggi.
- **Pain Point:** Alat monitoring yang ada terlalu berat atau mahal untuk skala kecil.

---

## 5. Ruang Lingkup Proyek

### 5.1 Dalam Lingkup (In Scope)

- Bot Telegram sebagai antarmuka utama pengguna.
- Manajemen sistem Linux (CPU, RAM, disk, network, proses).
- Manajemen layanan systemd.
- Manajemen kontainer Docker dan Docker Compose.
- Manajemen pengguna sistem.
- Penjadwalan tugas (cron-like scheduler internal).
- Notifikasi otomatis (alert threshold).
- Sistem plugin berbasis arsitektur.
- Autentikasi berbasis Telegram User ID.
- Role-Based Access Control (RBAC).
- Audit log seluruh tindakan.
- Backup dan restore konfigurasi bot.
- Integrasi AI Gateway (opsional, plug-and-play).
- Deployment sebagai systemd service di Debian 12 / Ubuntu Server.
- Antarmuka berbasis menu Telegram (inline keyboard).

### 5.2 Di Luar Lingkup (Out of Scope) untuk v1.0

- Web dashboard berbasis browser.
- Mobile application native.
- Manajemen DNS otomatis.
- Manajemen sertifikat SSL secara mandiri (tanpa Nginx/Certbot).
- Dukungan Windows Server.
- Dukungan macOS.
- Marketplace plugin online.
- Multi-tenant (satu bot untuk banyak VPS berbeda secara terdistribusi).

---

## 6. Fitur Versi Pertama (MVP)

### 6.1 Modul Sistem (System Module)

| ID Fitur | Nama Fitur | Deskripsi | Prioritas |
|----------|-----------|-----------|-----------|
| SYS-001 | Info Server | Tampilkan informasi server: hostname, OS, kernel, uptime | P0 |
| SYS-002 | Monitor CPU | Tampilkan penggunaan CPU real-time dan per-core | P0 |
| SYS-003 | Monitor RAM | Tampilkan penggunaan RAM, swap, dan buffer | P0 |
| SYS-004 | Monitor Disk | Tampilkan penggunaan disk semua mount point | P0 |
| SYS-005 | Monitor Network | Tampilkan traffic jaringan dan statistik interface | P1 |
| SYS-006 | Daftar Proses | Tampilkan proses dengan resource usage tertinggi | P1 |
| SYS-007 | Kill Proses | Hentikan proses berdasarkan PID | P1 |
| SYS-008 | System Update | Jalankan apt update dan apt upgrade | P1 |
| SYS-009 | Reboot Server | Reboot server dengan konfirmasi dua langkah | P0 |
| SYS-010 | Shutdown Server | Shutdown server dengan konfirmasi dua langkah | P1 |

### 6.2 Modul Layanan (Service Module)

| ID Fitur | Nama Fitur | Deskripsi | Prioritas |
|----------|-----------|-----------|-----------|
| SVC-001 | Daftar Layanan | Tampilkan daftar semua systemd service | P0 |
| SVC-002 | Status Layanan | Tampilkan status dan log singkat layanan | P0 |
| SVC-003 | Start Layanan | Jalankan layanan systemd | P0 |
| SVC-004 | Stop Layanan | Hentikan layanan systemd | P0 |
| SVC-005 | Restart Layanan | Restart layanan systemd | P0 |
| SVC-006 | Enable Layanan | Enable layanan agar auto-start saat boot | P1 |
| SVC-007 | Disable Layanan | Disable layanan dari auto-start | P1 |
| SVC-008 | Log Layanan | Tampilkan log journald layanan (50 baris terakhir) | P0 |

### 6.3 Modul Docker (Docker Module)

| ID Fitur | Nama Fitur | Deskripsi | Prioritas |
|----------|-----------|-----------|-----------|
| DCK-001 | Daftar Kontainer | Tampilkan semua kontainer (running dan stopped) | P0 |
| DCK-002 | Start Kontainer | Jalankan kontainer Docker | P0 |
| DCK-003 | Stop Kontainer | Hentikan kontainer Docker | P0 |
| DCK-004 | Restart Kontainer | Restart kontainer Docker | P0 |
| DCK-005 | Log Kontainer | Tampilkan log kontainer (100 baris terakhir) | P0 |
| DCK-006 | Stats Kontainer | Tampilkan statistik resource kontainer | P1 |
| DCK-007 | Pull Image | Pull Docker image terbaru | P1 |
| DCK-008 | Daftar Image | Tampilkan semua Docker image | P1 |
| DCK-009 | Hapus Image | Hapus Docker image yang tidak digunakan | P2 |
| DCK-010 | Docker Compose Up | Jalankan docker compose up -d | P1 |
| DCK-011 | Docker Compose Down | Jalankan docker compose down | P1 |

### 6.4 Modul Notifikasi (Notification Module)

| ID Fitur | Nama Fitur | Deskripsi | Prioritas |
|----------|-----------|-----------|-----------|
| NOT-001 | Alert CPU | Kirim notifikasi jika CPU > threshold | P0 |
| NOT-002 | Alert RAM | Kirim notifikasi jika RAM > threshold | P0 |
| NOT-003 | Alert Disk | Kirim notifikasi jika disk > threshold | P0 |
| NOT-004 | Alert Service Down | Kirim notifikasi jika layanan crash | P0 |
| NOT-005 | Alert Login | Kirim notifikasi saat ada yang login ke bot | P1 |
| NOT-006 | Alert Reboot | Kirim notifikasi setelah server reboot | P1 |
| NOT-007 | Konfigurasi Threshold | Atur threshold alert per metrik | P1 |

### 6.5 Modul Autentikasi & Keamanan (Auth & Security Module)

| ID Fitur | Nama Fitur | Deskripsi | Prioritas |
|----------|-----------|-----------|-----------|
| SEC-001 | Whitelist User | Hanya User ID terdaftar yang bisa mengakses | P0 |
| SEC-002 | Role Assignment | Assign role Admin/Operator/Viewer ke user | P0 |
| SEC-003 | Audit Log | Catat semua perintah yang dijalankan | P0 |
| SEC-004 | Rate Limiting | Batasi jumlah perintah per user per menit | P1 |
| SEC-005 | Emergency Lock | Kunci semua akses kecuali super admin | P1 |

### 6.6 Modul Penjadwalan (Scheduler Module)

| ID Fitur | Nama Fitur | Deskripsi | Prioritas |
|----------|-----------|-----------|-----------|
| SCH-001 | Tambah Jadwal | Tambah tugas terjadwal (cron expression) | P1 |
| SCH-002 | Daftar Jadwal | Tampilkan semua jadwal aktif | P1 |
| SCH-003 | Hapus Jadwal | Hapus jadwal | P1 |
| SCH-004 | Laporan Berkala | Kirim laporan status server setiap X jam | P1 |

---

## 7. Fitur Masa Depan

### Roadmap v1.1

- Plugin Nginx: Kelola konfigurasi virtual host Nginx langsung dari Telegram.
- Plugin Firewall: Kelola iptables/ufw dari Telegram.
- Plugin SSH Key Manager: Kelola authorized_keys pengguna server.
- Plugin Fail2ban: Pantau dan kelola Fail2ban dari Telegram.

### Roadmap v1.2

- Plugin Cloudflare: Kelola DNS record dan status tunnel Cloudflare.
- Plugin Certbot: Renew sertifikat SSL dan tampilkan status kedaluwarsa.
- Plugin Netdata: Tampilkan grafik metrik Netdata di Telegram.
- Plugin CasaOS: Kelola aplikasi CasaOS dari Telegram.

### Roadmap v2.0

- Multi-Server Management: Satu bot mengelola beberapa VPS sekaligus.
- AI-Powered Analysis: Analisis log server menggunakan LLM dan berikan saran pemecahan masalah.
- Plugin Marketplace: Repositori plugin komunitas yang dapat diinstall dengan satu perintah.
- Web Dashboard (Read-Only): Tampilan monitoring berbasis web yang disinkronkan dengan bot.
- Backup Otomatis ke Google Drive/S3.

### Roadmap v3.0

- Kluster Manajemen: Orkestrasi sederhana untuk server dalam satu jaringan.
- Self-Healing: Bot dapat mengambil tindakan otomatis berdasarkan aturan yang dikonfigurasi.
- Natural Language Commands: Perintah berbasis bahasa alami menggunakan LLM.

---

## 8. User Journey

### Journey 1: Setup Pertama Kali

```
[Developer] -> Unduh repositori -> Jalankan setup.sh -> Masukkan Bot Token & User ID
     -> Bot aktif sebagai systemd service -> Kirim /start ke bot
     -> Bot menyapa dan menampilkan menu utama -> Pengguna menjelajahi fitur
```

### Journey 2: Monitoring Harian

```
[Developer] -> Buka Telegram -> Kirim /status atau tekan tombol "Status"
     -> Bot tampilkan ringkasan CPU, RAM, Disk, Uptime
     -> Pengguna lihat ada layanan yang down
     -> Tekan tombol "Restart" -> Bot minta konfirmasi
     -> Pengguna konfirmasi -> Bot restart layanan -> Kirim laporan hasil
```

### Journey 3: Menerima Alert Otomatis

```
[Bot - Background Scheduler] -> Deteksi CPU > 90% selama 5 menit
     -> Kirim notifikasi ke semua Admin/Operator
     -> Admin buka Telegram -> Lihat notifikasi dengan tombol "Cek Proses"
     -> Tekan tombol -> Bot tampilkan top processes
     -> Admin kill proses yang bermasalah -> Bot konfirmasi
```

### Journey 4: Operator dengan Akses Terbatas

```
[Operator] -> Coba jalankan /reboot -> Bot cek role
     -> Role Operator tidak diizinkan reboot -> Bot kirim pesan error yang jelas
     -> Operator restart layanan web yang diizinkan -> Bot eksekusi
     -> Audit log mencatat tindakan dengan timestamp dan user info
```

---

## 9. Use Case Utama

### UC-001: Memantau Status Server

**Aktor:** Admin, Operator, Viewer
**Trigger:** Pengguna mengirim perintah /status
**Pre-condition:** Pengguna terautentikasi dan memiliki role aktif

**Alur Utama:**
1. Pengguna mengirim /status
2. Bot memvalidasi identitas pengguna
3. Bot mengumpulkan metrik sistem (CPU, RAM, Disk, Uptime)
4. Bot memformat data dalam pesan yang rapi
5. Bot mengirim respons dengan inline keyboard untuk aksi lanjutan

**Alur Alternatif:**
- Jika user tidak dikenal, bot mengirim pesan penolakan

**Post-condition:** Pengguna menerima laporan status server terkini

---

### UC-002: Restart Layanan Kritis

**Aktor:** Admin, Operator
**Trigger:** Pengguna memilih restart dari menu layanan
**Pre-condition:** Pengguna memiliki role Admin atau Operator

**Alur Utama:**
1. Pengguna pilih layanan dari daftar
2. Bot tampilkan status layanan saat ini
3. Pengguna pilih "Restart"
4. Bot minta konfirmasi dengan tombol Ya/Tidak
5. Pengguna tekan "Ya"
6. Bot jalankan `systemctl restart <service>`
7. Bot tunggu 3 detik lalu cek status
8. Bot kirim hasil dengan status terbaru dan log singkat
9. Tindakan dicatat di audit log

**Alur Alternatif:**
- Jika layanan gagal restart, bot kirim pesan error dengan log troubleshooting

---

### UC-003: Menerima dan Merespons Alert

**Aktor:** Bot (sistem)
**Trigger:** Scheduler mendeteksi metrik melewati threshold
**Pre-condition:** Fitur alert aktif dan threshold dikonfigurasi

**Alur Utama:**
1. Scheduler cek metrik setiap interval yang dikonfigurasi
2. Metrik melewati threshold
3. Bot kirim notifikasi ke semua penerima alert yang dikonfigurasi
4. Notifikasi berisi informasi metrik dan tombol aksi cepat

---

## 10. Non-Functional Requirement

### 10.1 Performa

| Metrik | Nilai Target |
|--------|-------------|
| Waktu respons perintah baca (status, list) | < 2 detik |
| Waktu respons perintah tulis (restart, stop) | < 5 detik |
| Latensi notifikasi alert | < 10 detik dari deteksi |
| Penggunaan CPU bot dalam kondisi idle | < 1% |
| Penggunaan RAM bot dalam kondisi idle | < 50 MB |
| Penggunaan RAM bot dalam kondisi sibuk | < 150 MB |

### 10.2 Keandalan (Reliability)

| Metrik | Nilai Target |
|--------|-------------|
| Target uptime | 99.5% per bulan |
| Recovery otomatis dari crash | < 10 detik (via systemd restart) |
| Persistensi data setelah restart | 100% (SQLite on-disk) |
| Toleransi kehilangan koneksi Telegram API | Auto-reconnect tanpa kehilangan state |

### 10.3 Keamanan

- Seluruh operasi berbasis whitelist User ID Telegram.
- Zero perintah dieksekusi dari user yang tidak terdaftar.
- Seluruh perintah dicatat di audit log.
- Credential tidak pernah disimpan dalam kode.
- Sandboxing untuk eksekusi perintah shell.

### 10.4 Maintainability

- Setiap plugin dapat diaktifkan/dinonaktifkan tanpa restart bot (kecuali plugin core).
- Penambahan plugin baru tidak memerlukan perubahan kode inti.
- Seluruh modul memiliki unit test dengan coverage > 80%.

### 10.5 Portabilitas

- Didukung: Debian 12 (Bookworm), Ubuntu 22.04 LTS, Ubuntu 24.04 LTS.
- Python 3.12+ required.
- Tidak bergantung pada distribusi-spesifik package manager selain apt.

---

## 11. Batasan Sistem

### 11.1 Batasan Teknis

1. **Satu Server per Instance:** Satu instance bot mengelola satu server. Multi-server adalah fitur v2.0.
2. **Python Only:** Seluruh kode inti ditulis dalam Python 3.12+. Tidak ada microservice berbahasa lain.
3. **SQLite sebagai Default:** Database default adalah SQLite untuk kemudahan deployment.
4. **Koneksi Internet Wajib:** Bot memerlukan koneksi ke Telegram API.
5. **Root atau Sudo Required:** Beberapa operasi memerlukan akses privileged.
6. **Linux Only:** Target sistem adalah Linux.

### 11.2 Batasan Bisnis

1. **Open Source:** Seluruh kode harus terbuka dan berlisensi MIT.
2. **Tidak Ada Cloud Backend:** Bot berjalan sepenuhnya di VPS pengguna.
3. **Tidak Ada Biaya Wajib:** Fungsionalitas inti sepenuhnya gratis.

### 11.3 Ketergantungan Eksternal

| Dependensi | Tujuan | Risiko |
|------------|--------|--------|
| Telegram Bot API | Antarmuka utama | Medium (downtime Telegram) |
| Python 3.12+ | Runtime | Low |
| systemd | Service management | Low |
| Docker Engine | Container management | Low (opsional) |
| AI Provider API | Fitur AI | Low (opsional) |

---

## 12. Roadmap Pengembangan

```
FASE 0 - Fondasi (Bulan 1)
--------------------------------------------------
  Dokumentasi arsitektur lengkap
  Setup repositori, CI/CD pipeline dasar
  Core engine: bot lifecycle, auth, plugin manager
  Database schema & migration system

FASE 1 - MVP (Bulan 2-3)
--------------------------------------------------
  Plugin: System Monitor (CPU, RAM, Disk, Network)
  Plugin: Service Manager (systemd)
  Plugin: Docker Manager
  Plugin: Alert & Notification
  Plugin: Scheduler
  Telegram UX: menu, keyboard, format pesan
  Deployment: systemd service setup script
  Testing: unit test untuk semua plugin core

FASE 2 - Stabilisasi & Komunitas (Bulan 4-5)
--------------------------------------------------
  Plugin: Nginx Manager
  Plugin: Firewall (UFW)
  Plugin: SSH Key Manager
  Plugin: Fail2ban Monitor
  Dokumentasi kontributor lengkap

FASE 3 - Ekosistem (Bulan 6-9)
--------------------------------------------------
  Plugin: Cloudflare Integration
  Plugin: CasaOS Manager
  Plugin: Backup Manager (Google Drive, S3)
  AI Gateway: analisis log dengan LLM

FASE 4 - Skalabilitas (Bulan 10-12)
--------------------------------------------------
  Multi-server management
  Plugin marketplace protokol
  Self-healing rules engine
  Web dashboard (read-only)
```

---

## 13. Keputusan Desain

| Keputusan | Pilihan | Alasan |
|-----------|---------|--------|
| Antarmuka utama | Telegram Bot | Tersedia di seluruh platform, aman, gratis, tidak perlu buat UI sendiri |
| Bahasa pemrograman | Python 3.12+ | Ekosistem kaya, async support, mudah dikontribusi, library bot matang |
| Database | SQLite | Zero-config, file-based, mudah di-backup, dapat dimigrasi ke PostgreSQL |
| Service runtime | systemd | Native di target OS, auto-restart, log terintegrasi dengan journald |
| Plugin architecture | Discovery-based | Memungkinkan plugin ditambah tanpa ubah kode inti |
| Satu bot per server | Single-instance | Menyederhanakan keamanan, deployment, dan debugging untuk v1.0 |

---

## 14. Checklist Implementasi

### Fase 0 (Fondasi)

- [ ] Repositori GitHub dibuat dengan struktur folder yang benar
- [ ] Semua 10 dokumen teknis selesai dan di-review
- [ ] File README.md utama dibuat
- [ ] File LICENSE (MIT) dibuat
- [ ] File .gitignore dibuat
- [ ] GitHub Actions workflow dasar dikonfigurasi

### Fase 1 (MVP)

- [ ] Core engine selesai dan teruji
- [ ] Sistem autentikasi berfungsi
- [ ] Plugin system dapat memuat plugin dari folder
- [ ] Minimal 5 plugin core berfungsi
- [ ] Deployment script (setup.sh) berfungsi di Debian 12 fresh install
- [ ] Unit test coverage lebih dari 80% untuk core engine
- [ ] Dokumentasi pengguna (README) tersedia

### Fase 2 (Stabilisasi)

- [ ] Semua plugin dari Roadmap v1.1 selesai
- [ ] Integration test otomatis berjalan di CI
- [ ] Panduan kontributor tersedia di CONTRIBUTING.md
- [ ] Panduan pengembangan plugin tersedia

---

*Dokumen ini adalah bagian dari seri dokumentasi teknis Serverinka Guardian.*
*Dokumen terkait: 02_SYSTEM_ARCHITECTURE.md, 03_TECH_STACK.md, 04_DATABASE_DESIGN.md, 05_API_DESIGN.md, 06_SECURITY.md, 07_PLUGIN_SYSTEM.md, 08_TELEGRAM_BOT.md, 09_DEPLOYMENT.md, 10_DEVELOPMENT_RULES.md*
