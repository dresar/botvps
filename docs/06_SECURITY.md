# 06 — Keamanan Sistem
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [05_API_DESIGN.md](05_API_DESIGN.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Model Ancaman (Threat Model)](#2-model-ancaman-threat-model)
3. [Autentikasi Berbasis Telegram User ID](#3-autentikasi-berbasis-telegram-user-id)
4. [Role-Based Access Control (RBAC)](#4-role-based-access-control-rbac)
5. [Audit Log](#5-audit-log)
6. [Rate Limiting](#6-rate-limiting)
7. [Secret Management](#7-secret-management)
8. [Validasi Command & Input](#8-validasi-command--input)
9. [Sandbox Command Execution](#9-sandbox-command-execution)
10. [Whitelist & Blacklist](#10-whitelist--blacklist)
11. [Emergency Mode](#11-emergency-mode)
12. [Backup Key & Recovery Plan](#12-backup-key--recovery-plan)
13. [Keamanan Jaringan](#13-keamanan-jaringan)
14. [Keamanan Database](#14-keamanan-database)
15. [Keamanan Deployment](#15-keamanan-deployment)
16. [Security Checklist Deployment](#16-security-checklist-deployment)
17. [Keputusan Desain](#17-keputusan-desain)
18. [Checklist Implementasi](#18-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan seluruh aspek keamanan Serverinka Guardian. Keamanan adalah fondasi arsitektur, bukan tambahan. Setiap fitur harus didesain dengan mempertimbangkan model ancaman yang relevan. Dokumen ini menjadi referensi wajib bagi seluruh kontributor.

---

## 2. Model Ancaman (Threat Model)

### 2.1 Aktor Ancaman

| Aktor | Kemampuan | Target | Dampak |
|-------|-----------|--------|--------|
| **Penyerang Eksternal** | Mengirim pesan ke bot jika tahu bot token | Mengeksekusi perintah server | Tinggi |
| **Pengguna Tidak Sah** | Mengirim pesan ke bot dengan User ID yang tidak terdaftar | Mendapatkan akses ke server | Tinggi |
| **Pengguna dengan Role Rendah** | User terdaftar dengan role viewer/operator | Eskalasi privilege, eksekusi perintah tidak diizinkan | Sedang |
| **Bot Token Bocor** | Mendapatkan bot token dari repositori atau log | Kirim perintah sebagai bot | Tinggi |
| **Credential Bocor** | Mendapatkan file .env | Akses semua konfigurasi termasuk API key | Tinggi |
| **Server Compromise** | Akses fisik atau root ke server | Membaca database dan konfigurasi | Sangat Tinggi |

### 2.2 Vektor Serangan Utama

1. **Bot Token Hijacking** — Token bot bocor, memungkinkan penyerang mengirim perintah.
2. **Unauthorized Access** — User yang tidak terdaftar mencoba mengakses bot.
3. **Privilege Escalation** — User dengan role rendah mencoba menjalankan perintah yang tidak diizinkan.
4. **Command Injection** — Input berbahaya yang menyisipkan perintah OS dalam parameter.
5. **Denial of Service** — User mengirim ribuan perintah untuk membebani bot.
6. **Log Injection** — Input yang memanipulasi format log untuk menyembunyikan aktivitas.
7. **Backup File Exposure** — File backup database yang berisi data sensitif tersebar.

---

## 3. Autentikasi Berbasis Telegram User ID

### 3.1 Mekanisme Autentikasi

Serverinka Guardian menggunakan **Telegram User ID** sebagai identifier identitas pengguna. Telegram User ID bersifat:
- **Unik:** Tidak ada dua pengguna Telegram dengan ID yang sama.
- **Permanen:** ID tidak berubah meskipun username diganti.
- **Tidak dapat dipalsukan:** Telegram menjamin integritas User ID melalui bot token.
- **Tersedia otomatis:** Setiap update dari Telegram menyertakan User ID pengirim.

### 3.2 Alur Autentikasi

```
Update diterima dari Telegram API
     |
     v
Middleware: AuthMiddleware.process()
     |
     +-- Ekstrak user_id dari update
     |
     +-- Query UserRepository.find_by_telegram_id(user_id)
     |
     +-- Jika user tidak ditemukan:
     |     -> Log "UNAUTHORIZED_ACCESS_ATTEMPT"
     |     -> Kirim pesan: "Akses ditolak. Hubungi administrator."
     |     -> Publish event: "auth.user_denied"
     |     -> STOP (tidak proses update lebih lanjut)
     |
     +-- Jika user ditemukan tapi is_active=False:
     |     -> Kirim pesan: "Akun Anda tidak aktif."
     |     -> STOP
     |
     +-- Jika user ditemukan tapi is_blocked=True:
     |     -> Kirim pesan: "Akun Anda diblokir sementara."
     |     -> STOP
     |
     +-- User valid -> Lanjutkan ke middleware berikutnya
     |   Update informasi user (username, full_name) di database
```

### 3.3 Super Admin Bootstrap

Super admin ditentukan melalui environment variable `TELEGRAM_ADMIN_USER_IDS` (comma-separated) di file `.env`. Saat aplikasi start, jika User ID tersebut belum ada di database, sistem akan menambahkannya otomatis dengan role `super_admin`.

```
TELEGRAM_ADMIN_USER_IDS=123456789,987654321
```

**Penting:** Super admin yang ditentukan via env var tidak dapat di-deactivate atau di-downgrade role-nya melalui bot.

### 3.4 Keamanan Bot Token

- Bot token hanya disimpan di file `.env` yang dilindungi permission file system.
- Bot token tidak pernah muncul di log, pesan error, atau output apapun.
- Jika bot token bocor: buat token baru melalui @BotFather dan update file .env.

---

## 4. Role-Based Access Control (RBAC)

### 4.1 Definisi Role

| Role | Deskripsi | Siapa |
|------|-----------|-------|
| `super_admin` | Akses penuh, termasuk manajemen user dan emergency mode | Owner server (via .env) |
| `admin` | Akses penuh ke semua operasi server, tidak bisa manage super_admin | Admin tim |
| `operator` | Akses ke operasi operasional (start/stop/restart), tidak bisa hapus/reboot | Anggota tim operasional |
| `viewer` | Hanya dapat melihat status, tidak dapat mengubah apapun | Stakeholder non-teknis |

### 4.2 Permission Matrix

| Permission | super_admin | admin | operator | viewer |
|------------|:-----------:|:-----:|:--------:|:------:|
| Lihat status server | YES | YES | YES | YES |
| Lihat log layanan | YES | YES | YES | YES |
| Lihat daftar kontainer | YES | YES | YES | YES |
| Restart layanan | YES | YES | YES | NO |
| Start/Stop layanan | YES | YES | YES | NO |
| Restart kontainer | YES | YES | YES | NO |
| Kill proses | YES | YES | YES | NO |
| System update (apt) | YES | YES | NO | NO |
| Reboot server | YES | YES | NO | NO |
| Shutdown server | YES | NO | NO | NO |
| Manage user | YES | YES | NO | NO |
| Tambah/hapus admin | YES | NO | NO | NO |
| Konfigurasi alert | YES | YES | NO | NO |
| Konfigurasi scheduler | YES | YES | NO | NO |
| Emergency lock | YES | NO | NO | NO |
| Lihat audit log | YES | YES | NO | NO |
| Manage plugin | YES | NO | NO | NO |

### 4.3 Implementasi Permission Check

Setiap command handler mendefinisikan `required_permissions` sebagai list string. Middleware akan memeriksa permission sebelum handler dieksekusi.

```
Contoh permission strings:
  "system:read"           -> Lihat status
  "system:write"          -> Operasi modifikasi sistem
  "system:reboot"         -> Reboot/shutdown server
  "service:read"          -> Lihat status layanan
  "service:write"         -> Start/stop/restart layanan
  "docker:read"           -> Lihat kontainer
  "docker:write"          -> Start/stop/restart kontainer
  "user:read"             -> Lihat daftar user
  "user:write"            -> Tambah/ubah/hapus user
  "audit:read"            -> Baca audit log
  "plugin:manage"         -> Kelola plugin
  "emergency:activate"    -> Aktifkan emergency mode
```

### 4.4 Permission Mapping per Role

```
super_admin -> ["*"]  (semua permission)

admin -> [
    "system:read", "system:write", "system:reboot",
    "service:read", "service:write",
    "docker:read", "docker:write",
    "user:read", "user:write",
    "audit:read",
    "scheduler:read", "scheduler:write",
    "alert:read", "alert:write"
]

operator -> [
    "system:read",
    "service:read", "service:write",
    "docker:read", "docker:write",
    "scheduler:read",
    "alert:read"
]

viewer -> [
    "system:read",
    "service:read",
    "docker:read"
]
```

---

## 5. Audit Log

### 5.1 Prinsip Audit Log

- **Semua tindakan dicatat:** Tanpa terkecuali, setiap perintah dari setiap user dicatat.
- **Tidak dapat dihapus:** Audit log tidak dapat dihapus melalui bot, hanya melalui akses database langsung.
- **Immutable setelah dibuat:** Record audit log tidak diupdate, hanya dibuat dan diselesaikan.
- **Tersedia untuk admin:** Admin dapat melihat audit log melalui command `/audit`.

### 5.2 Yang Dicatat

Setiap record audit log menyimpan:
- Siapa (telegram_id, user_id)
- Apa (action: "docker.restart")
- Target (container_name: "nginx")
- Parameter ({"force": false})
- Kapan (created_at)
- Hasil (success, failed, denied)
- Durasi (duration_ms)
- Error jika ada (error_message)

### 5.3 Retention Policy

- Audit log disimpan selama **90 hari** secara default.
- Konfigurasi dapat diubah via `AUDIT_LOG_RETENTION_DAYS` di `.env`.
- Cleanup dilakukan oleh scheduled job setiap tengah malam.

---

## 6. Rate Limiting

### 6.1 Mekanisme Rate Limiting

Rate limiter menggunakan **sliding window algorithm** berdasarkan hitungan command dalam rentang waktu.

```
Konfigurasi default:
  RATE_LIMIT_COMMANDS_PER_WINDOW = 30
  RATE_LIMIT_WINDOW_SECONDS = 60

Pengecekan:
  Hitung perintah user dalam 60 detik terakhir dari audit_logs
  Jika >= 30: kirim pesan "Terlalu banyak perintah. Tunggu X detik."
  Jika < 30: izinkan perintah
```

### 6.2 Pengecualian Rate Limit

Super admin tidak terkena rate limit. Ini dikonfigurasi di middleware dan tidak dapat diubah melalui bot.

### 6.3 Penanganan Rate Limit

Ketika user terkena rate limit:
1. Bot kirim pesan dengan estimasi waktu tunggu.
2. Pesan ini tidak dicatat di audit log (mencegah log flooding).
3. Percobaan berulang setelah warning dicatat sebagai `rate_limited` di audit log.

---

## 7. Secret Management

### 7.1 Prinsip

- **Zero Secret in Code:** Tidak ada secret (token, API key, password) dalam kode.
- **Zero Secret in Version Control:** File `.env` dan file konfigurasi tidak pernah di-commit.
- **Least Privilege:** Setiap komponen hanya menerima secret yang dibutuhkan.
- **Rotation Ready:** Secret dapat dirotasi tanpa perubahan kode.

### 7.2 Hierarki Secret

```
Level 1 (Kritis): TELEGRAM_BOT_TOKEN
  -> Kontrol penuh bot
  -> Simpan di /etc/serverinka/guardian.env (mode 600, owner: serverinka)

Level 2 (Sensitif): AI_API_KEY, GOOGLE_DRIVE_CREDENTIALS
  -> Simpan di /etc/serverinka/guardian.env

Level 3 (Konfigurasi): Database path, log level, threshold values
  -> Simpan di /etc/serverinka/guardian.env atau database
```

### 7.3 File Permission

```
/etc/serverinka/             -> drwxr-x--- root:serverinka
/etc/serverinka/guardian.env -> -rw------- serverinka:serverinka (600)
/var/lib/serverinka/         -> drwxr-x--- serverinka:serverinka (750)
/var/lib/serverinka/guardian.db -> -rw-r------ serverinka:serverinka (640)
/opt/serverinka/guardian/    -> drwxr-xr-x root:serverinka (755)
```

### 7.4 Rotasi Bot Token

Jika bot token perlu dirotasi:
1. Buat token baru melalui @BotFather.
2. Update `/etc/serverinka/guardian.env`.
3. Restart service: `systemctl restart serverinka-guardian`.
4. Verifikasi bot berjalan normal.

---

## 8. Validasi Command & Input

### 8.1 Prinsip Validasi

- **Semua input dianggap tidak aman** sampai divalidasi.
- Validasi dilakukan di middleware sebelum sampai ke handler.
- Input yang tidak valid di-reject dengan pesan error yang jelas.

### 8.2 Validasi Nama Layanan (systemd)

```
Rules:
  - Karakter yang diizinkan: [a-zA-Z0-9._-]
  - Maksimal 256 karakter
  - Tidak boleh mengandung: .., /, shell metacharacter
  - Harus diakhiri dengan .service, .socket, .timer, atau tanpa ekstensi

Contoh valid: nginx, nginx.service, postgresql@14-main.service
Contoh invalid: ../etc/passwd, nginx; rm -rf /, nginx$(whoami)
```

### 8.3 Validasi Nama Kontainer Docker

```
Rules:
  - Karakter yang diizinkan: [a-zA-Z0-9_.-]
  - Maksimal 128 karakter
  - Tidak boleh kosong
  - Tidak boleh mengandung shell metacharacter
```

### 8.4 Validasi PID

```
Rules:
  - Harus berupa bilangan bulat positif
  - Harus dalam range 1 - 4194304 (max PID Linux)
  - PID proses sistem kritis (1, 2) tidak dapat di-kill melalui bot
```

### 8.5 Validasi Cron Expression

```
Rules:
  - Harus terdiri dari 5 field (menit jam hari bulan day-of-week)
  - Divalidasi menggunakan library APScheduler (akan raise error jika tidak valid)
  - Interval minimum: setiap 5 menit (mencegah overload)
```

---

## 9. Sandbox Command Execution

### 9.1 Prinsip Sandboxing

Semua eksekusi perintah OS dilakukan melalui `SubprocessSandbox`, bukan langsung menggunakan `subprocess.run()` dengan shell=True.

### 9.2 Aturan Sandbox

```
DILARANG:
  - subprocess.run(cmd, shell=True) <- TIDAK PERNAH
  - os.system(cmd)                  <- TIDAK PERNAH
  - eval(user_input)                <- TIDAK PERNAH
  - exec(user_input)                <- TIDAK PERNAH

WAJIB:
  - subprocess.run(["systemctl", "restart", service_name], ...)
    (list of arguments, bukan string)
  - Input validation sebelum masuk ke subprocess
  - Timeout untuk semua subprocess calls
  - Capture stdout dan stderr
```

### 9.3 Command Whitelist

Hanya perintah yang ada dalam whitelist yang dapat dieksekusi:

```
ALLOWED_COMMANDS = {
    "systemctl": {
        "allowed_subcommands": ["start", "stop", "restart", "enable", "disable", "status", "is-active", "is-enabled"],
        "timeout_seconds": 30
    },
    "journalctl": {
        "allowed_flags": ["-u", "-n", "--no-pager", "-b", "--since"],
        "timeout_seconds": 10
    },
    "apt-get": {
        "allowed_subcommands": ["update", "upgrade", "list"],
        "timeout_seconds": 300
    },
    "kill": {
        "allowed_signals": ["-15", "-9"],  # SIGTERM, SIGKILL
        "timeout_seconds": 5
    }
}
```

### 9.4 Timeout & Resource Limits

```
Semua subprocess calls memiliki timeout:
  - Read operations (status, list): 10 detik
  - Write operations (start, stop, restart): 30 detik
  - Update operations (apt-get): 300 detik
  - Kill operation: 5 detik

Jika timeout tercapai:
  -> Proses di-terminate
  -> Error dikembalikan ke user
  -> Event dicatat di audit log
```

---

## 10. Whitelist & Blacklist

### 10.1 User Whitelist

Hanya User ID Telegram yang terdaftar di database (tabel `users`) yang dapat menggunakan bot. Tidak ada "open registration" — semua user harus ditambahkan oleh admin.

### 10.2 Service Whitelist (Opsional)

Admin dapat mengonfigurasi whitelist layanan yang boleh dikelola melalui bot. Jika whitelist dikonfigurasi, hanya layanan dalam whitelist yang dapat di-manage.

```
Konfigurasi di plugin_configs:
  plugin_name: "service_manager"
  config_key: "service_whitelist"
  config_value: "nginx,postgresql,redis" (kosong = semua layanan diizinkan)
```

### 10.3 Service Blacklist

Layanan yang TIDAK BOLEH dikelola melalui bot, meskipun super admin memintanya:

```
SYSTEM_PROTECTED_SERVICES = [
    "serverinka-guardian",  # Bot itu sendiri (ada mekanisme restart khusus)
    "systemd-journald",
    "systemd-udevd",
    "dbus",
    "sshd",                 # Bisa diizinkan secara eksplisit oleh super_admin
]
```

### 10.4 Container Blacklist

Kontainer yang tidak boleh dihentikan melalui bot:

```
PROTECTED_CONTAINERS = []  # Dikonfigurasi oleh admin via plugin_configs
```

---

## 11. Emergency Mode

### 11.1 Definisi

Emergency Mode adalah kondisi di mana **semua akses ke bot diblokir sementara**, kecuali super_admin. Ini berguna ketika terjadi insiden keamanan atau perlu melakukan maintenance kritikal.

### 11.2 Aktivasi Emergency Mode

Hanya super_admin yang dapat mengaktifkan emergency mode:
```
Command: /emergency lock
Konfirmasi: Ya/Tidak
Efek: Semua user (termasuk admin) tidak dapat menjalankan perintah apapun
      Notifikasi dikirim ke semua user yang terdaftar
      Dicatat di audit log
```

### 11.3 Menonaktifkan Emergency Mode

```
Command: /emergency unlock
Hanya super_admin yang bisa menonaktifkan
Notifikasi dikirim ke semua user
Dicatat di audit log
```

### 11.4 Status Emergency Mode

Disimpan di database `plugin_configs`:
```
plugin_name: "core"
config_key: "emergency_mode"
config_value: "true" / "false"
```

---

## 12. Backup Key & Recovery Plan

### 12.1 Skenario Kehilangan Akses Bot

**Skenario:** Super admin tidak dapat mengakses Telegram / bot tidak merespons.

**Recovery Plan:**
1. SSH langsung ke server VPS.
2. Cek status bot: `systemctl status serverinka-guardian`.
3. Cek log: `journalctl -u serverinka-guardian -n 50`.
4. Jika perlu reset, edit database langsung: `sqlite3 /var/lib/serverinka/guardian.db`.
5. Atau restore dari backup: `cp /var/lib/serverinka/backups/guardian_latest.db.gz`.

### 12.2 Skenario Bot Token Bocor

1. Segera buat bot token baru via @BotFather: `/revoke` lama, buat baru.
2. SSH ke server, update token di `/etc/serverinka/guardian.env`.
3. Restart bot: `systemctl restart serverinka-guardian`.
4. Verifikasi di Telegram bahwa bot merespons.
5. Review audit log untuk tindakan yang dilakukan dengan token lama.

### 12.3 Skenario Database Corrupt

1. Stop bot: `systemctl stop serverinka-guardian`.
2. Verifikasi: `sqlite3 /var/lib/serverinka/guardian.db "PRAGMA integrity_check;"`.
3. Jika corrupt, restore backup: `cp /var/lib/serverinka/backups/guardian_YYYYMMDD.db.gz.bak /var/lib/serverinka/guardian.db`.
4. Jalankan migrasi jika backup lebih lama dari versi saat ini.
5. Start bot: `systemctl start serverinka-guardian`.

### 12.4 Backup Key Information (Dokumentasi Offline)

Admin wajib menyimpan informasi berikut di tempat yang aman (password manager, dll):
- Telegram User ID super admin.
- Nama file .env dan lokasi backup.
- Prosedur SSH ke server.
- Instruksi recovery dasar.

---

## 13. Keamanan Jaringan

### 13.1 Koneksi ke Telegram API

- Koneksi menggunakan HTTPS, dikelola oleh python-telegram-bot.
- Tidak ada endpoint jaringan yang dibuka oleh bot (kecuali mode webhook).
- Mode default (long polling) tidak memerlukan port terbuka.

### 13.2 Mode Webhook (Opsional)

Jika webhook diaktifkan:
- Harus menggunakan HTTPS dengan sertifikat SSL yang valid.
- Port yang digunakan harus dibatasi oleh firewall hanya menerima dari IP Telegram.
- IP range Telegram: https://core.telegram.org/resources/cidr.txt

### 13.3 Firewall Rekomendasi

```
Rekomendasi UFW:
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow ssh                     # Port 22 atau custom SSH port
  ufw allow 443/tcp                 # Jika webhook digunakan
  ufw enable
```

---

## 14. Keamanan Database

### 14.1 Perlindungan File Database

- File database hanya dapat dibaca oleh user `serverinka`.
- Permission file: `640` (owner read/write, group read).
- Tidak ada akses database dari jaringan (SQLite adalah file-based).

### 14.2 SQL Injection Prevention

- Seluruh query menggunakan parameterized queries (prepared statements).
- Tidak ada string concatenation untuk membangun SQL query.
- Input dari user tidak pernah langsung dimasukkan ke SQL.

### 14.3 Sensitive Data Handling

- Tidak ada password atau credential yang disimpan di database.
- Audit log menyimpan `telegram_id` (bukan informasi pribadi yang sensitif).
- Data yang disimpan di `parameters` JSON di-sanitize dari informasi sensitif.

---

## 15. Keamanan Deployment

### 15.1 Dedicated User

Bot berjalan sebagai user `serverinka` yang:
- Bukan root.
- Tidak memiliki password login.
- Tidak dapat SSH langsung.
- Memiliki sudo rules terbatas untuk operasi yang diperlukan.

### 15.2 Sudo Rules

```
# /etc/sudoers.d/serverinka
serverinka ALL=(root) NOPASSWD: /bin/systemctl start *
serverinka ALL=(root) NOPASSWD: /bin/systemctl stop *
serverinka ALL=(root) NOPASSWD: /bin/systemctl restart *
serverinka ALL=(root) NOPASSWD: /bin/systemctl enable *
serverinka ALL=(root) NOPASSWD: /bin/systemctl disable *
serverinka ALL=(root) NOPASSWD: /bin/systemctl status *
serverinka ALL=(root) NOPASSWD: /bin/journalctl *
serverinka ALL=(root) NOPASSWD: /usr/bin/apt-get update
serverinka ALL=(root) NOPASSWD: /usr/bin/apt-get upgrade -y
serverinka ALL=(root) NOPASSWD: /sbin/reboot
serverinka ALL=(root) NOPASSWD: /sbin/shutdown
```

### 15.3 Systemd Hardening

```
[Service]
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/serverinka /var/log/serverinka
CapabilityBoundingSet=
```

---

## 16. Security Checklist Deployment

Checklist yang harus diverifikasi sebelum deployment production:

- [ ] File `.env` memiliki permission `600` dan dimiliki oleh user `serverinka`
- [ ] Bot token tidak ada di log, kode, atau repositori
- [ ] User `serverinka` tidak memiliki password login
- [ ] Firewall aktif dengan aturan minimal
- [ ] SSH menggunakan key-based auth (bukan password)
- [ ] Super admin User ID dikonfigurasi dengan benar di `.env`
- [ ] Database backup terjadwal berjalan
- [ ] Audit log dapat diakses oleh admin melalui bot
- [ ] Rate limiting dikonfigurasi dan berjalan
- [ ] Emergency mode dapat diaktifkan
- [ ] Prosedur recovery telah didokumentasikan

---

## 17. Keputusan Desain

### Mengapa Telegram User ID, Bukan Username?

Username Telegram dapat berubah kapan saja. User ID adalah permanen dan tidak dapat dipalsukan selama bot token aman. Menggunakan User ID sebagai identifier mencegah serangan berbasis perubahan username.

### Mengapa Tidak Ada Password atau OTP?

Telegram sendiri sudah menyediakan autentikasi yang kuat (2FA). Menambahkan password atau OTP akan memperburuk pengalaman pengguna tanpa manfaat keamanan yang signifikan, selama bot token terlindungi dengan baik.

### Mengapa Whitelist, Bukan Blacklist?

Pendekatan whitelist (deny-by-default) jauh lebih aman. Dengan blacklist, satu kelalaian dapat memberikan akses tidak sah. Dengan whitelist, pengguna harus secara eksplisit ditambahkan oleh admin.

### Mengapa `shell=False` di Subprocess?

`shell=True` memungkinkan shell injection. Dengan `shell=False` dan argument list, setiap token adalah argument terpisah yang tidak diinterpretasikan sebagai shell command. Ini adalah mitigasi utama untuk command injection.

---

## 18. Checklist Implementasi

### Autentikasi

- [ ] `AuthMiddleware` memvalidasi setiap update dari Telegram
- [ ] Super admin di-bootstrap dari environment variable saat startup
- [ ] User yang tidak ada di whitelist mendapat pesan "Akses Ditolak"
- [ ] Unit test untuk semua skenario autentikasi

### RBAC

- [ ] Permission matrix diimplementasi sebagai lookup table di `AuthService`
- [ ] Setiap command handler mendefinisikan required permissions
- [ ] Middleware memeriksa permission sebelum handler dieksekusi
- [ ] Unit test untuk semua kombinasi role dan permission

### Audit Log

- [ ] Semua tindakan dicatat di tabel `audit_logs`
- [ ] Tidak ada tindakan yang terlewat dari audit
- [ ] Cleanup job untuk retention policy berjalan
- [ ] Unit test untuk audit log service

### Rate Limiting

- [ ] `RateLimitMiddleware` menggunakan sliding window
- [ ] Super admin dikecualikan dari rate limit
- [ ] Unit test untuk rate limiting

### Input Validation

- [ ] Semua input divalidasi sebelum digunakan
- [ ] Nama layanan divalidasi dengan regex
- [ ] PID divalidasi sebagai integer dalam range valid
- [ ] Unit test untuk semua validator

### Subprocess Sandboxing

- [ ] `SubprocessSandbox` diimplementasi dan digunakan di semua tempat
- [ ] `shell=False` di semua subprocess calls
- [ ] Timeout dikonfigurasi untuk semua subprocess
- [ ] Command whitelist diterapkan
- [ ] Unit test untuk sandbox

---

*Referensi: [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [04_DATABASE_DESIGN.md](04_DATABASE_DESIGN.md) | [05_API_DESIGN.md](05_API_DESIGN.md) | [09_DEPLOYMENT.md](09_DEPLOYMENT.md)*
