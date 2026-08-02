# 08 — Desain Telegram Bot UX
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [01_PRD.md](01_PRD.md) | [06_SECURITY.md](06_SECURITY.md) | [07_PLUGIN_SYSTEM.md](07_PLUGIN_SYSTEM.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Prinsip UX Telegram Bot](#2-prinsip-ux-telegram-bot)
3. [Command Tree Lengkap](#3-command-tree-lengkap)
4. [Menu Utama & Navigasi](#4-menu-utama--navigasi)
5. [Callback & Inline Keyboard Conventions](#5-callback--inline-keyboard-conventions)
6. [Format Pesan Standar](#6-format-pesan-standar)
7. [Emoji Guideline](#7-emoji-guideline)
8. [Pagination System](#8-pagination-system)
9. [Confirmation Pattern](#9-confirmation-pattern)
10. [Notifikasi Otomatis](#10-notifikasi-otomatis)
11. [Error Handling UX](#11-error-handling-ux)
12. [Dashboard Ringkasan](#12-dashboard-ringkasan)
13. [Multi-Language Readiness](#13-multi-language-readiness)
14. [Command Namespace & Routing](#14-command-namespace--routing)
15. [Keputusan Desain](#15-keputusan-desain)
16. [Checklist Implementasi](#16-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan keseluruhan pengalaman pengguna (UX) di Telegram untuk Serverinka Guardian. Mencakup command tree, desain menu, format pesan, emoji, notifikasi, dan semua aspek interaksi pengguna. Konsistensi UX adalah kunci kepercayaan pengguna.

---

## 2. Prinsip UX Telegram Bot

1. **Respons cepat:** Selalu kirim "loading" state untuk operasi > 1 detik.
2. **Konfirmasi untuk operasi destruktif:** Reboot, shutdown, kill, stop — semua memerlukan konfirmasi.
3. **Pesan yang informatif:** Setiap respons harus memberikan konteks yang cukup untuk tindak lanjut.
4. **Navigasi yang konsisten:** Setiap menu memiliki tombol "Kembali" dan "Menu Utama".
5. **Error yang ramah:** Pesan error menjelaskan apa yang salah dan apa yang bisa dilakukan.
6. **Jangan banjiri pesan:** Gunakan edit_message daripada send_message untuk update status.
7. **Format yang bersih:** Gunakan monospace untuk data teknis, bold untuk label penting.
8. **Mobile-first:** Pertimbangkan tampilan di layar smartphone (lebar terbatas).

---

## 3. Command Tree Lengkap

### Command Tingkat 1 (Dapat langsung dikirim ke bot)

```
/start              -> Tampilkan sambutan dan menu utama
/help               -> Tampilkan panduan command
/status             -> Dashboard ringkasan server (shortcut)
/menu               -> Tampilkan menu utama (sama dengan /start setelah auth)
/cancel             -> Batalkan operasi yang sedang berlangsung
```

### Command Tingkat 2 (Didaftarkan oleh plugin, accessible via /help dan menu)

```
SISTEM:
  /system info      -> Info server lengkap
  /system cpu       -> Penggunaan CPU detail
  /system ram       -> Penggunaan RAM detail
  /system disk      -> Penggunaan Disk detail
  /system net       -> Statistik jaringan
  /system proc      -> Daftar proses teratas
  /system update    -> Jalankan system update (admin)
  /system reboot    -> Reboot server (admin, konfirmasi)
  /system shutdown  -> Shutdown server (super_admin, konfirmasi)

LAYANAN (SYSTEMD):
  /service list     -> Daftar layanan
  /service [nama]   -> Status layanan tertentu
  /service start [nama]   -> Jalankan layanan (operator+)
  /service stop [nama]    -> Hentikan layanan (operator+)
  /service restart [nama] -> Restart layanan (operator+)
  /service log [nama]     -> Log layanan (50 baris)

DOCKER:
  /docker list      -> Daftar kontainer
  /docker [nama]    -> Detail kontainer
  /docker start [nama]   -> Jalankan kontainer (operator+)
  /docker stop [nama]    -> Hentikan kontainer (operator+)
  /docker restart [nama] -> Restart kontainer (operator+)
  /docker log [nama]     -> Log kontainer (100 baris)
  /docker images    -> Daftar Docker image
  /docker pull [image]   -> Pull image baru (admin)

ALERT & NOTIFIKASI:
  /alert list       -> Daftar konfigurasi alert
  /alert set [metric] [threshold]  -> Atur threshold alert (admin)
  /alert test       -> Kirim test alert (admin)
  /alert toggle [id]-> Toggle aktif/nonaktif alert (admin)

JADWAL:
  /schedule list    -> Daftar jadwal aktif
  /schedule add     -> Tambah jadwal baru (admin, interactive)
  /schedule del [id]-> Hapus jadwal (admin)
  /schedule toggle [id] -> Toggle aktif/nonaktif (admin)

PENGGUNA:
  /user list        -> Daftar pengguna terdaftar (admin)
  /user add [id] [role] -> Tambah pengguna (admin)
  /user role [id] [role] -> Ubah role pengguna (admin)
  /user remove [id] -> Hapus/nonaktifkan pengguna (admin)

AUDIT:
  /audit            -> Tampilkan audit log terbaru (admin)
  /audit [user_id]  -> Audit log user tertentu (admin)

PENGATURAN:
  /settings         -> Menu pengaturan bot (admin)

DARURAT:
  /emergency lock   -> Aktifkan emergency mode (super_admin)
  /emergency unlock -> Nonaktifkan emergency mode (super_admin)
```

---

## 4. Menu Utama & Navigasi

### 4.1 Menu Utama

```
========================================
🤖 Serverinka Guardian
🖥️  hostname.server.com
✅  Online | Uptime: 7h 23m
========================================

Pilih menu:

[📊 Status]          [⚙️ Layanan]
[🐳 Docker]          [🔔 Alert]
[📅 Jadwal]          [👥 Pengguna]
[📋 Audit Log]       [⚙️ Pengaturan]
```

### 4.2 Menu Sistem / Status

```
========================================
📊 Status Server
========================================

🖥️  Hostname: hostname.server.com
🐧  OS: Debian 12 (Bookworm)
⏱️  Uptime: 7 jam 23 menit 45 detik
🕐  Boot: 2 Agustus 2026 05:00 WIB

CPU:  ████████░░  82%  (4 core)
RAM:  ██████░░░░  61%  (3.9/6.4 GB)
Disk: ███░░░░░░░  28%  (28/100 GB)
Load: 1.23 | 1.05 | 0.92

[🔄 Refresh] [🔢 Proses] [🌐 Jaringan]
[📥 Update OS] [🔁 Reboot] [⬅️ Menu]
```

### 4.3 Menu Docker

```
========================================
🐳 Docker Containers (8 aktif / 10 total)
========================================

▶️  nginx         (running)   🟢
▶️  redis         (running)   🟢
▶️  postgres      (running)   🟢
▶️  nextcloud     (running)   🟢
⏹️  jellyfin      (stopped)   🔴
▶️  portainer     (running)   🟢
▶️  uptime-kuma   (running)   🟢
⏹️  gitea         (stopped)   🔴
▶️  vaultwarden   (running)   🟢
▶️  traefik       (running)   🟢

[⬅️ Kembali] [🔄 Refresh] [🖼️ Images]
```

### 4.4 Detail Kontainer

```
========================================
🐳 nginx
========================================

Status:  🟢 Running
Image:   nginx:alpine
ID:      a1b2c3d4e5f6
Dibuat:  1 Agt 2026, 08:00 WIB

CPU:   2.3%
RAM:   45.2 MB / 512 MB

Ports:
  0.0.0.0:80  -> 80/tcp
  0.0.0.0:443 -> 443/tcp

[▶️ Start] [⏹️ Stop] [🔄 Restart]
[📋 Log]   [📊 Stats]
[⬅️ Kembali]
```

---

## 5. Callback & Inline Keyboard Conventions

### 5.1 Format Callback Data

Callback data menggunakan format yang konsisten untuk routing:

```
Format: "{namespace}:{action}:{target}:{extra}"

Contoh:
  "docker:detail:nginx"           -> Tampilkan detail kontainer nginx
  "docker:restart:nginx"          -> Request restart nginx
  "docker:confirm_restart:nginx"  -> Konfirmasi restart nginx
  "docker:log:nginx:100"          -> Ambil 100 baris log nginx

  "service:detail:nginx.service"
  "service:restart:nginx.service"
  "service:confirm_restart:nginx.service"

  "nav:main_menu"                 -> Kembali ke menu utama
  "nav:back:{context}"            -> Kembali ke halaman sebelumnya
  "nav:page:{context}:{page_num}" -> Navigasi halaman

  "confirm:yes:{action}:{target}" -> Konfirmasi "Ya"
  "confirm:no"                    -> Konfirmasi "Tidak" / Batal
```

### 5.2 Panjang Callback Data

Telegram membatasi callback data hingga **64 byte**. Jika data melebihi batas, simpan state di database sessions dan gunakan ID numerik sebagai callback data.

```
Jika nama target terlalu panjang:
  1. Simpan {"action": "restart", "target": "nama_kontainer_panjang"} di sessions
  2. Callback data: "session:{session_id}"
  3. Handler ambil detail dari database
```

### 5.3 Keyboard Builder Conventions

```
Standard navigation row (selalu di baris terakhir):
  [⬅️ Kembali]  [🏠 Menu Utama]

Standard action rows:
  Read-only actions (view, refresh) -> Baris pertama
  Write actions (start, stop, restart) -> Baris kedua
  Destructive actions (hapus, reboot) -> Baris terakhir sebelum navigasi

Button label format:
  "{emoji} {Label}"   <- Selalu gunakan emoji di depan label
  Contoh: "🔄 Restart", "⏹️ Stop", "▶️ Start"
```

---

## 6. Format Pesan Standar

### 6.1 Parse Mode

Gunakan **HTML** sebagai parse mode default (bukan Markdown). Alasan: lebih aman dari karakter konflik, lebih predictable.

```
Bold:      <b>teks tebal</b>
Italic:    <i>teks miring</i>
Monospace: <code>kode</code>
Block:     <pre>blok kode</pre>
Link:      <a href="url">teks</a>
```

### 6.2 Template Pesan Sukses

```
✅ Berhasil

<b>Layanan nginx direstart</b>

Status: <code>active (running)</code>
Waktu:  2 Agustus 2026, 12:30:45 WIB
Oleh:   Ahmad Fauzi
```

### 6.3 Template Pesan Error

```
❌ Gagal

<b>Tidak dapat merestart layanan nginx</b>

Alasan: Layanan tidak ditemukan di sistem.

Saran: Periksa nama layanan dengan /service list
```

### 6.4 Template Pesan Informasi

```
ℹ️ Info

<b>Tentang Serverinka Guardian</b>

Versi: 1.0.0
Python: 3.12.4
Uptime Bot: 3 hari 14 jam
Plugin aktif: 8
```

### 6.5 Template Pesan Konfirmasi

```
⚠️ Konfirmasi

<b>Restart layanan nginx?</b>

Layanan akan dihentikan sementara selama proses restart.
Estimasi downtime: 2-5 detik.

[✅ Ya, Restart]  [❌ Tidak, Batal]
```

### 6.6 Template Pesan Loading

```
⏳ Memproses...

Merestart layanan nginx, mohon tunggu.
```

### 6.7 Aturan Panjang Pesan

- Pesan maksimal: 4096 karakter (batas Telegram).
- Jika melebihi: potong dan tambahkan halaman atau tombol "Lanjut".
- Untuk log panjang: kirim sebagai dokumen (file .txt) bukan teks biasa.

---

## 7. Emoji Guideline

### 7.1 Status Emoji

| Status | Emoji | Konteks |
|--------|-------|---------|
| Running / Active / OK | 🟢 ✅ | Layanan berjalan, operasi berhasil |
| Stopped / Inactive | 🔴 ⏹️ | Layanan berhenti, error |
| Loading / Processing | ⏳ 🔄 | Sedang memproses |
| Warning | ⚠️ 🟡 | Peringatan, perlu perhatian |
| Info | ℹ️ | Informasi umum |
| Error / Failed | ❌ | Operasi gagal |
| Denied / Blocked | 🚫 | Akses ditolak |
| Locked / Secure | 🔒 | Mode darurat, keamanan |

### 7.2 Sistem & Resource Emoji

| Konteks | Emoji |
|---------|-------|
| CPU | 🖥️ |
| RAM / Memory | 💾 |
| Disk | 💿 |
| Network | 🌐 |
| Proses | ⚡ |
| Docker | 🐳 |
| Layanan / systemd | ⚙️ |
| Jadwal / Cron | 📅 |
| Notifikasi / Alert | 🔔 |
| Log | 📋 |
| Pengguna | 👤 👥 |
| Pengaturan | ⚙️ |
| Keamanan | 🔐 |
| Backup | 💾 |
| Bot | 🤖 |
| Server | 🖥️ |
| Reboot | 🔁 |
| Shutdown | 🔌 |

### 7.3 Navigasi Emoji

| Aksi | Emoji |
|------|-------|
| Kembali | ⬅️ |
| Menu Utama | 🏠 |
| Refresh | 🔄 |
| Lanjut / Next | ➡️ |
| Sebelumnya / Prev | ⬅️ |
| Tambah / Baru | ➕ |
| Hapus | 🗑️ |
| Edit | ✏️ |

---

## 8. Pagination System

### 8.1 Kapan Menggunakan Pagination

Gunakan pagination jika jumlah item melebihi batas tampilan layar:
- Daftar kontainer Docker: > 8 item per halaman.
- Daftar layanan systemd: > 8 item per halaman.
- Daftar pengguna: > 10 item per halaman.
- Log: > 20 baris per halaman (atau tampilkan sebagai file).
- Audit log: > 10 item per halaman.

### 8.2 Format Pagination

```
Pesan dengan pagination:

🐳 Docker Containers (Halaman 2/3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶️ container-9   (running) 🟢
▶️ container-10  (running) 🟢
...

[⬅️ Prev]  [Hal 2/3]  [Next ➡️]
[🏠 Menu Utama]
```

### 8.3 Implementasi Pagination

```
Callback data untuk navigasi:
  "nav:page:docker_list:1"   -> Halaman 1 daftar kontainer
  "nav:page:docker_list:2"   -> Halaman 2 daftar kontainer
  "nav:page:audit_log:1"     -> Halaman 1 audit log

Page size dikonfigurasi per menu:
  DEFAULT_PAGE_SIZE = 8
```

---

## 9. Confirmation Pattern

### 9.1 Level Konfirmasi

Berdasarkan tingkat risiko operasi:

| Level | Operasi | Konfirmasi |
|-------|---------|------------|
| 0 | Read (status, list, log) | Tidak perlu konfirmasi |
| 1 | Write (start, stop, restart) | Satu klik konfirmasi |
| 2 | Berbahaya (kill proses, delete) | Satu klik konfirmasi + delay 3 detik |
| 3 | Kritis (reboot, shutdown, emergency) | Dua klik konfirmasi |

### 9.2 Implementasi Konfirmasi Level 1

```
[User tekan Stop Container]
     |
     v
Bot: "Konfirmasi stop kontainer nginx?"
     [✅ Ya, Stop]  [❌ Tidak]
     |
     +-- Ya: Eksekusi, kirim hasil
     +-- Tidak: "Dibatalkan" (hapus keyboard)
```

### 9.3 Implementasi Konfirmasi Level 3 (Reboot)

```
[User kirim /system reboot]
     |
     v
Bot: "⚠️ REBOOT SERVER?"
     Semua layanan akan berhenti sebentar.
     [✅ Ya, Lanjut]  [❌ Tidak]
     |
     +-- Tidak: "Dibatalkan."
     +-- Ya: Bot tanya lagi:
              "🔴 KONFIRMASI AKHIR: Yakin reboot sekarang?"
              [🔁 REBOOT SEKARANG]  [❌ Batal]
                    |
                    +-- Batal: "Dibatalkan."
                    +-- REBOOT: Eksekusi, bot kirim "Server akan reboot..."
                                Bot tidak dapat merespons selama reboot
```

### 9.4 Session State untuk Konfirmasi

State konfirmasi disimpan di tabel `sessions` dengan TTL 60 detik. Jika pengguna tidak merespons dalam 60 detik, konfirmasi otomatis dibatalkan.

---

## 10. Notifikasi Otomatis

### 10.1 Format Notifikasi Alert

```
🚨 ALERT — Server hostname.server.com

<b>Penggunaan Disk Tinggi</b>

Metrik:   Disk /
Nilai:    <code>92%</code>  (Threshold: 90%)
Waktu:    2 Agustus 2026, 13:45:00 WIB

[📊 Cek Status]  [⚙️ Detail Disk]
```

### 10.2 Format Notifikasi Layanan Down

```
⚠️ LAYANAN DOWN — hostname.server.com

<b>Layanan postgresql.service berhenti</b>

Status:   <code>failed (Result: exit-code)</code>
Waktu:    2 Agustus 2026, 14:00:15 WIB
PID:      (none)

[🔄 Restart]  [📋 Lihat Log]  [📊 Status]
```

### 10.3 Format Notifikasi Laporan Berkala

```
📊 Laporan Berkala — 14:00 WIB

<b>hostname.server.com</b>

CPU:  45% (avg 1 jam)
RAM:  61%
Disk: 28%

Layanan:
  ✅ nginx       (running)
  ✅ postgres    (running)
  ✅ redis       (running)
  ✅ docker      (running)

⏱️ Uptime: 7 jam 23 menit
```

### 10.4 Format Notifikasi Setelah Reboot

```
✅ Server Online Kembali

<b>hostname.server.com</b> telah reboot dan kembali online.

Waktu online: 2 Agustus 2026, 14:05:30 WIB
Waktu reboot: ~5 menit
```

---

## 11. Error Handling UX

### 11.1 Kategori Error dan Pesan Pengguna

| Kategori Error | Pesan ke Pengguna |
|----------------|-------------------|
| Akses ditolak | "🚫 Akses Ditolak\nAnda tidak memiliki izin untuk perintah ini." |
| Rate limit | "⏳ Terlalu Banyak Perintah\nCoba lagi dalam {X} detik." |
| Layanan tidak ditemukan | "❌ Layanan tidak ditemukan\nPeriksa nama dengan /service list" |
| Kontainer tidak ditemukan | "❌ Kontainer tidak ditemukan\nPeriksa nama dengan /docker list" |
| Docker tidak tersedia | "❌ Docker tidak tersedia\nDocker daemon mungkin tidak berjalan." |
| Operasi timeout | "⏳ Timeout\nOperasi memakan waktu terlalu lama. Cek status secara manual." |
| Error tak terduga | "❌ Terjadi Kesalahan\nError dicatat. Hubungi administrator jika berlanjut." |

### 11.2 Prinsip Pesan Error

1. Selalu jelaskan APA yang salah.
2. Selalu berikan SARAN tindak lanjut jika memungkinkan.
3. Jangan tampilkan stack trace atau detail teknis ke pengguna.
4. Jangan abaikan error secara diam-diam (silent error).
5. Catat detail teknis di log, bukan di pesan pengguna.

---

## 12. Dashboard Ringkasan

### 12.1 Komponen Dashboard (/status)

Dashboard menampilkan semua informasi penting dalam satu pesan:

```
🤖 Serverinka Guardian v1.0.0
🖥️  hostname.server.com

━━━ STATUS SISTEM ━━━
⏱️  Uptime: 7 jam 23 menit
🕐  Waktu: 14:05:30 WIB

CPU:  ████████░░  82%  | Load: 1.23
RAM:  ██████░░░░  61%  | 3.9/6.4 GB
Disk: ███░░░░░░░  28%  | 28/100 GB

━━━ LAYANAN KRITIS ━━━
🟢 nginx        🟢 postgres
🟢 redis        🟢 docker

━━━ DOCKER ━━━
8 running | 2 stopped | 10 total

━━━ ALERT AKTIF ━━━
Tidak ada alert aktif ✅

[🔄 Refresh] [⚙️ Detail] [🐳 Docker]
[📋 Log]    [👥 User]   [🏠 Menu]
```

### 12.2 Progress Bar Format

Progress bar diimplementasi menggunakan karakter Unicode:

```
0-10%:   ░░░░░░░░░░
10-20%:  █░░░░░░░░░
...
90-100%: █████████░
100%:    ██████████

Kode: filled = "█", empty = "░", width = 10
Rumus: filled_count = round(percent / 10)
```

### 12.3 Refresh Otomatis Dashboard

Dashboard tidak di-refresh secara otomatis. Pengguna harus menekan tombol "Refresh" untuk mendapatkan data terbaru. Ini menghindari API rate limit Telegram dari edit_message yang terlalu sering.

---

## 13. Multi-Language Readiness

### 13.1 Strategi Internasionalisasi

Versi 1.0 menggunakan Bahasa Indonesia sebagai bahasa utama. Arsitektur disiapkan untuk multi-language di versi berikutnya.

**Persiapan:**
- Semua string pesan pengguna disimpan di file `messages.py` masing-masing plugin, bukan di-hardcode dalam handler.
- Gunakan key-based string format: `msg("docker.restart.success", container_name="nginx")`.
- File `messages.py` berisi dictionary `{key: {lang_code: template_string}}`.

### 13.2 Bahasa yang Direncanakan

| Bahasa | Kode | Status |
|--------|------|--------|
| Indonesia | id | Default, v1.0 |
| Inggris | en | v1.1 |

### 13.3 User Language Preference

Preferensi bahasa disimpan di kolom `language_code` di tabel `users`. Default: `id`.

Pengguna dapat mengubah bahasa melalui:
```
/settings language en
/settings language id
```

---

## 14. Command Namespace & Routing

### 14.1 Telegram BotCommand Registration

Command yang didaftarkan ke Telegram (muncul di autocomplete):

```
Untuk semua user:
  /start     - Mulai bot
  /help      - Bantuan
  /status    - Status server
  /menu      - Menu utama
  /cancel    - Batalkan operasi

Untuk user dengan role viewer ke atas:
  /service   - Manajemen layanan
  /docker    - Manajemen Docker
  /alert     - Konfigurasi alert

Untuk operator ke atas:
  /system    - Informasi sistem

Untuk admin ke atas:
  /user      - Manajemen pengguna
  /schedule  - Jadwal tugas
  /audit     - Audit log
  /settings  - Pengaturan bot
```

### 14.2 Routing Rules

```
Input: "/docker list"
  -> parse command: "docker"
  -> parse args: ["list"]
  -> find handler for namespace="docker", command="list"
  -> check permission: user has "docker:read"? (yes)
  -> execute handler

Input: "/status"
  -> shortcut mapping: "status" -> namespace="system", command="status"
  -> find handler for namespace="system", command="status"
  -> execute handler

Input: "teks biasa bukan command"
  -> cek apakah user dalam state conversation (sessions table)
  -> jika ya: teruskan ke conversation handler yang aktif
  -> jika tidak: kirim pesan "Gunakan /help untuk melihat command yang tersedia"
```

---

## 15. Keputusan Desain

### Mengapa HTML, Bukan MarkdownV2?

MarkdownV2 memerlukan escaping banyak karakter khusus (-, ., (, ), dll.) yang rawan bug dan sulit di-debug. HTML lebih predictable: hanya `<`, `>`, `&` yang perlu di-escape. Semua komponen pesan di-sanitize sebelum dikirim.

### Mengapa Tidak Ada Auto-Refresh Dashboard?

Auto-refresh menggunakan `edit_message` secara periodik dapat memicu rate limit Telegram API. Lebih baik membiarkan pengguna mengontrol kapan mereka ingin data terbaru dengan menekan tombol Refresh.

### Mengapa Inline Keyboard, Bukan Reply Keyboard?

Inline keyboard lebih fleksibel: dapat diupdate tanpa mengirim pesan baru, dapat di-attach ke pesan spesifik, dan tidak mengotori input field pengguna. Reply keyboard lebih cocok untuk bot yang benar-benar conversational, bukan control panel.

### Mengapa Emoji di Awal Label Tombol?

Emoji membantu pengguna mengenali aksi secara visual lebih cepat dari membaca teks. Di layar kecil smartphone, pola visual ini sangat membantu. Konsistensi emoji juga membangun "bahasa visual" yang mudah dipelajari.

---

## 16. Checklist Implementasi

### Command Infrastructure

- [ ] Semua command Telegram didaftarkan via `set_my_commands` API
- [ ] Router menangani namespace.command dengan benar
- [ ] Shortcut command (/status, /help, /start) berfungsi
- [ ] /cancel berfungsi untuk membatalkan conversation yang aktif

### Message Templates

- [ ] Semua template pesan dibuat di messages.py masing-masing plugin
- [ ] HTML escaping diterapkan pada semua input pengguna yang ditampilkan
- [ ] Progress bar function diimplementasi dan diuji
- [ ] Long message auto-split berfungsi

### Keyboard Builder

- [ ] Semua format callback data konsisten
- [ ] Pagination keyboard berfungsi untuk semua daftar
- [ ] Confirmation pattern Level 1, 2, 3 diimplementasi
- [ ] Tombol navigasi (Kembali, Menu Utama) ada di setiap halaman

### Notifications

- [ ] Alert notification dikirim saat threshold terlampaui
- [ ] Service down notification berfungsi
- [ ] Laporan berkala (jika dijadwalkan) berfungsi
- [ ] Notifikasi reboot berfungsi (sent via job setelah startup)

### Dashboard

- [ ] /status menampilkan semua komponen dashboard
- [ ] Refresh button memperbarui data
- [ ] Data real-time dari SystemService

---

*Referensi: [01_PRD.md](01_PRD.md) | [05_API_DESIGN.md](05_API_DESIGN.md) | [06_SECURITY.md](06_SECURITY.md) | [07_PLUGIN_SYSTEM.md](07_PLUGIN_SYSTEM.md)*
