# 07 — Sistem Plugin
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [05_API_DESIGN.md](05_API_DESIGN.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Filosofi Plugin System](#2-filosofi-plugin-system)
3. [Struktur Plugin](#3-struktur-plugin)
4. [Plugin Metadata](#4-plugin-metadata)
5. [Plugin Lifecycle](#5-plugin-lifecycle)
6. [Dependency Injection](#6-dependency-injection)
7. [Command Registration](#7-command-registration)
8. [Event System & Hook System](#8-event-system--hook-system)
9. [Lazy Loading](#9-lazy-loading)
10. [Plugin Isolation & Error Handling](#10-plugin-isolation--error-handling)
11. [Plugin Configuration](#11-plugin-configuration)
12. [Plugin Versioning](#12-plugin-versioning)
13. [Contoh Alur Plugin Lengkap](#13-contoh-alur-plugin-lengkap)
14. [Panduan Membuat Plugin Baru](#14-panduan-membuat-plugin-baru)
15. [Plugin Bawaan (Built-in Plugins)](#15-plugin-bawaan-built-in-plugins)
16. [Keputusan Desain](#16-keputusan-desain)
17. [Checklist Implementasi](#17-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan arsitektur sistem plugin Serverinka Guardian secara lengkap. Plugin adalah unit fungsionalitas yang dapat ditambahkan, dimodifikasi, atau dihapus tanpa mengubah kode inti (core engine). Dokumen ini menjadi panduan wajib bagi siapa pun yang ingin membuat plugin baru.

---

## 2. Filosofi Plugin System

### Prinsip Utama

1. **Core Engine minimal:** Core engine hanya mengurus lifecycle, routing, auth, dan event. Semua fitur adalah plugin.
2. **Zero coupling antar plugin:** Plugin tidak boleh mengimport satu sama lain secara langsung. Komunikasi hanya melalui Event Bus.
3. **Plugin harus terisolasi:** Kegagalan satu plugin tidak boleh menghentikan plugin lain atau core engine.
4. **Fail-safe loading:** Jika plugin gagal dimuat, core berjalan tanpa plugin tersebut dan melaporkan error.
5. **Discovery otomatis:** Plugin ditemukan otomatis dari folder tanpa perlu registrasi manual.
6. **Satu tanggung jawab:** Setiap plugin mengelola satu domain (system, docker, nginx, dll).

### Apa yang BISA dilakukan Plugin

- Mendaftarkan command handler untuk namespace-nya.
- Mendaftarkan scheduled jobs.
- Mendengarkan dan mempublikasikan event.
- Membaca dan menulis konfigurasi plugin-nya sendiri ke database.
- Mengakses `ApplicationContext` untuk mendapatkan service yang dibutuhkan.
- Mendefinisikan repository-nya sendiri untuk akses data spesifik domain.

### Apa yang TIDAK BISA dilakukan Plugin

- Mengakses konfigurasi plugin lain secara langsung.
- Mengimport modul dari plugin lain secara langsung.
- Memodifikasi database schema (hanya core migration yang boleh).
- Mendaftarkan handler untuk namespace plugin lain.
- Memanggil fungsi internal core engine secara langsung (kecuali melalui ApplicationContext).

---

## 3. Struktur Plugin

Setiap plugin adalah sebuah **Python package** (direktori dengan `__init__.py`) di dalam folder `guardian/plugins/`.

### Struktur Standar

```
guardian/plugins/
  {nama_plugin}/
    __init__.py             <- Wajib ada, dapat kosong atau export PluginClass
    plugin.py               <- WAJIB: Entrypoint plugin, subclass dari BasePlugin
    handlers.py             <- WAJIB: Semua command dan callback handler
    service.py              <- DIREKOMENDASIKAN: Logika bisnis domain
    repository.py           <- OPSIONAL: Akses data spesifik plugin
    models.py               <- OPSIONAL: Dataclass dan model data plugin
    validators.py           <- OPSIONAL: Validasi input spesifik plugin
    keyboards.py            <- OPSIONAL: InlineKeyboard definitions
    messages.py             <- OPSIONAL: Template pesan untuk plugin
```

### Aturan Penamaan

- Nama direktori plugin: huruf kecil, underscore sebagai pemisah. Contoh: `service_manager`, `docker`, `nginx`.
- Nama class plugin: CamelCase + "Plugin". Contoh: `ServiceManagerPlugin`, `DockerPlugin`.
- Command namespace: sama dengan nama direktori plugin.

---

## 4. Plugin Metadata

Setiap plugin mendefinisikan metadata melalui class properties di `plugin.py`.

### Metadata Wajib

```
class MyPlugin(BasePlugin):

    name = "my_plugin"              # Identifier unik, sama dengan nama direktori
    version = "1.0.0"               # Semantic versioning: MAJOR.MINOR.PATCH
    description = "Deskripsi singkat plugin"
    author = "Nama Penulis"
    dependencies = []               # Nama plugin yang harus dimuat sebelum plugin ini
    min_core_version = "1.0.0"      # Versi minimum core engine yang dibutuhkan
    permissions_required = []       # Permission custom yang dibutuhkan plugin ini
```

### Contoh dengan Dependensi

```
class NginxPlugin(BasePlugin):

    name = "nginx"
    version = "1.0.0"
    description = "Manajemen Nginx dari Telegram"
    author = "Serverinka Team"
    dependencies = ["service_manager"]  # Nginx plugin bergantung pada service_manager
    min_core_version = "1.0.0"
    permissions_required = ["nginx:read", "nginx:write"]
```

---

## 5. Plugin Lifecycle

```
                    PLUGIN MANAGER START
                           |
                           v
               [DISCOVERY]
               Scan folder plugins/
               Temukan semua subpackage yang memiliki plugin.py
                           |
                           v
               [IMPORT]
               Import setiap plugin module
               Instansiasi PluginClass()
                           |
                           v
               [DEPENDENCY RESOLUTION]
               Build dependency graph
               Sort plugin berdasarkan urutan dependency
               Deteksi circular dependency (raise error)
                           |
                           v
               [VALIDATION]
               Validasi metadata setiap plugin
               Cek kompatibilitas versi core
               Cek permission yang dibutuhkan
                           |
                           v
               [SETUP] untuk setiap plugin (berurutan)
               await plugin.setup(ctx)
                 -> plugin mendaftarkan command handlers
                 -> plugin mendaftarkan event handlers
                 -> plugin mendaftarkan scheduled jobs
                 -> plugin inisialisasi resource
                           |
                           v
               [ACTIVE STATE]
               Plugin aktif, siap menerima command dan event
                           |
                     (Bot berjalan)
                           |
               [TEARDOWN SIGNAL]
               SIGTERM/SIGINT diterima atau restart bot
                           |
                           v
               [TEARDOWN] untuk setiap plugin (reverse order)
               await plugin.teardown()
                 -> plugin batalkan scheduled jobs
                 -> plugin tutup koneksi/resource
                 -> plugin simpan state jika perlu
                           |
                           v
               PLUGIN MANAGER STOP
```

### Plugin States

```
DISCOVERED -> LOADING -> ACTIVE -> TEARINGDOWN -> STOPPED
                |                                    ^
                v                                    |
             FAILED --------------------------------+
             (core continues without this plugin)
```

---

## 6. Dependency Injection

Plugin menerima semua dependensi melalui `ApplicationContext` yang diteruskan saat `setup()`. Plugin tidak boleh membuat instance service sendiri.

### ApplicationContext yang Tersedia di Plugin

```
Dalam plugin.setup(ctx: ApplicationContext):

ctx.config          -> GuardianSettings   (konfigurasi aplikasi)
ctx.database        -> DatabaseManager    (database connection manager)
ctx.event_bus       -> EventBus           (async event bus)
ctx.scheduler       -> SchedulerEngine    (scheduler engine)
ctx.bot             -> BotGateway         (telegram bot gateway)
ctx.auth            -> AuthService        (authentication service)
ctx.plugin_manager  -> PluginManager      (untuk query plugin lain - READ ONLY)
```

### Cara Mendapatkan Service

Plugin dapat membuat instance service-nya sendiri dengan meneruskan `ctx`:

```
Plugin setup:
    self.service = MyPluginService(ctx)
    self.repository = MyPluginRepository(ctx.database)
```

---

## 7. Command Registration

### Namespace System

Semua command menggunakan format `namespace.command`. Namespace adalah nama plugin.

```
Contoh:
  "system.status"    -> Plugin "system", command "status"
  "docker.list"      -> Plugin "docker", command "list"
  "service.restart"  -> Plugin "service_manager", command "restart"
```

### Cara Mendaftarkan Command

```
Dalam plugin.setup(ctx):

Daftarkan command handler:
  ctx.plugin_manager.register_command(
      namespace="docker",
      command="list",
      handler=self.handlers.handle_list,
      description="Tampilkan semua kontainer Docker",
      permissions=["docker:read"],
      args_schema=None
  )

Daftarkan callback handler:
  ctx.plugin_manager.register_callback(
      pattern="docker_action:",           <- Prefix callback data
      handler=self.handlers.handle_callback,
      permissions=["docker:read"]
  )
```

### CommandHandler Signature

```
Semua command handler harus memiliki signature:
  async def handle_xxx(self, cmd_ctx: CommandContext) -> None

Semua callback handler harus memiliki signature:
  async def handle_callback(self, cb_ctx: CallbackContext) -> None
```

### Telegram Command Mapping

Telegram hanya mendukung command format `/command`. Untuk command dengan namespace, digunakan dua pendekatan:

1. **Short command:** Perintah populer didaftarkan langsung tanpa namespace.
   ```
   /status   -> system.status
   /docker   -> docker.menu (tampilkan submenu docker)
   /services -> service_manager.menu
   ```

2. **Inline menu:** Pengguna berinteraksi melalui inline keyboard, bukan command teks. Ini adalah pendekatan utama.

---

## 8. Event System & Hook System

### Event Bus

Plugin berkomunikasi antar-plugin melalui Event Bus, bukan direct import.

```
Publish event (dari plugin A):
  await ctx.event_bus.publish(
      event_name="docker.container_restarted",
      payload={
          "container_id": "abc123",
          "container_name": "nginx",
          "restarted_by": 123456789
      }
  )

Subscribe event (dari plugin B):
  ctx.event_bus.subscribe(
      event_name="docker.container_restarted",
      handler=self.on_container_restarted
  )

Handler:
  async def on_container_restarted(self, payload: dict) -> None:
      # Lakukan sesuatu dengan informasi restart kontainer
      pass
```

### Lifecycle Hooks

Core engine mempublikasikan event lifecycle yang dapat didengarkan oleh plugin:

```
"system.startup_complete"     -> Bot selesai startup dan semua plugin aktif
"system.shutdown_requested"   -> Bot akan segera shutdown
"system.plugin_loaded"        -> Plugin berhasil dimuat (payload: plugin_name)
"auth.user_authenticated"     -> User baru berhasil auth (payload: user info)
"auth.user_denied"            -> User ditolak akses (payload: telegram_id)
```

### Best Practice Event

- Publish event setelah operasi berhasil, bukan sebelum.
- Payload event harus minimal dan hanya berisi informasi yang relevan.
- Handler event tidak boleh memblokir lama (gunakan asyncio.create_task jika perlu pekerjaan lama).
- Kegagalan handler event dicatat di log tapi tidak melempar exception ke publisher.

---

## 9. Lazy Loading

### Prinsip Lazy Loading

Plugin yang dinonaktifkan tidak dimuat sama sekali. Plugin yang bergantung pada layanan eksternal (seperti Docker) memeriksa ketersediaan layanan saat `setup()` dan men-disable diri sendiri jika layanan tidak tersedia.

### Disabling Plugin via Konfigurasi

```
Konfigurasi di .env:
  DISABLED_PLUGINS=nginx,cloudflare

Plugin yang ada di DISABLED_PLUGINS tidak akan di-load oleh Plugin Manager.
```

### Self-Disabling Plugin

```
Dalam DockerPlugin.setup():
  if not await self.service.is_available():
      self.logger.warning("Docker tidak tersedia. Plugin Docker dinonaktifkan.")
      raise PluginSetupError("Docker daemon tidak dapat diakses")
      # Plugin Manager tangkap error ini dan tandai plugin sebagai FAILED
      # Bot tetap berjalan tanpa plugin Docker
```

---

## 10. Plugin Isolation & Error Handling

### Isolation Guarantee

1. Setiap plugin berjalan dalam context yang sama (satu process asyncio), tapi error handling memastikan kegagalan plugin terisolasi.

2. Jika `plugin.setup()` raise exception:
   - Plugin ditandai sebagai FAILED.
   - Plugin lain yang bergantung pada plugin ini juga ditandai FAILED.
   - Bot tetap berjalan dengan plugin yang berhasil dimuat.
   - Super admin mendapat notifikasi plugin yang gagal.

3. Jika command handler raise unhandled exception:
   - Error ditangkap oleh middleware global.
   - Pesan error yang ramah dikirim ke pengguna.
   - Detail error dicatat di log.
   - Plugin tidak di-restart otomatis (harus restart bot untuk reload plugin).

4. Jika event handler raise exception:
   - Error dicatat di log.
   - Event bus melanjutkan pengiriman ke subscriber berikutnya.
   - Publisher tidak terpengaruh.

### Error Reporting

Plugin dapat melaporkan error ke pengguna melalui:
```
await cmd_ctx.bot.send_message(
    cmd_ctx.chat_id,
    "Gagal menjalankan perintah: {pesan_error}"
)
```

Plugin **tidak boleh** crash secara diam-diam. Setiap error harus dilaporkan ke log dan/atau pengguna.

---

## 11. Plugin Configuration

### Cara Plugin Menyimpan Konfigurasi

Plugin menggunakan `plugin_configs` tabel di database untuk konfigurasi yang dapat diubah melalui bot.

```
Menyimpan konfigurasi:
  await ctx.database.execute(
      "INSERT OR REPLACE INTO plugin_configs (plugin_name, config_key, config_value, value_type)
       VALUES (?, ?, ?, ?)",
      (self.name, "max_log_lines", "100", "integer")
  )

Membaca konfigurasi:
  value = await plugin_config_repository.get(
      plugin_name=self.name,
      config_key="max_log_lines",
      default="100"
  )
```

### Konfigurasi Default

Setiap plugin mendefinisikan konfigurasi default-nya di `DEFAULT_CONFIG` class variable:

```
class DockerPlugin(BasePlugin):

    DEFAULT_CONFIG = {
        "log_tail_lines": ("100", "integer", "Jumlah baris log yang ditampilkan"),
        "stats_refresh_seconds": ("5", "integer", "Interval refresh stats kontainer"),
        "show_stopped_containers": ("true", "boolean", "Tampilkan kontainer yang berhenti"),
    }
```

Saat `setup()`, plugin memastikan semua konfigurasi default ada di database.

---

## 12. Plugin Versioning

### Semantic Versioning

Plugin menggunakan semantic versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR:** Perubahan breaking (interface berubah, database schema berubah).
- **MINOR:** Fitur baru yang backward-compatible.
- **PATCH:** Bug fix.

### Kompatibilitas Core

Setiap plugin mendefinisikan `min_core_version`. Plugin Manager akan menolak memuat plugin jika versi core lebih rendah dari yang dibutuhkan plugin.

### Upgrade Plugin

1. Ganti file plugin di folder `plugins/`.
2. Restart bot: `systemctl restart serverinka-guardian`.
3. Plugin Manager akan memuat versi baru.
4. Jika ada perubahan database schema oleh plugin (masa depan), akan ada migration system khusus per-plugin.

---

## 13. Contoh Alur Plugin Lengkap

### Skenario: Plugin Docker - Restart Kontainer

```
STEP 1: User kirim /docker atau tekan tombol "Docker" di menu

STEP 2: BotGateway terima update
  -> AuthMiddleware: validasi user (OK, role=admin)
  -> RateLimitMiddleware: cek limit (OK)
  -> AuditMiddleware: catat perintah
  -> Router: temukan handler untuk namespace "docker", command "menu"

STEP 3: DockerPlugin.handlers.handle_menu(cmd_ctx) dipanggil
  -> Panggil DockerService.list_containers()
  -> Bangun InlineKeyboard dengan satu tombol per kontainer
  -> Kirim pesan: "Daftar Kontainer:" + keyboard
  -> Setiap tombol kontainer memiliki callback_data: "docker_container:nginx"

STEP 4: User tekan tombol "nginx" (callback query)
  -> BotGateway terima callback query update
  -> Auth + RateLimit + Audit middleware
  -> Router: temukan callback handler untuk pattern "docker_container:"
  -> DockerPlugin.handlers.handle_container_detail(cb_ctx) dipanggil
  -> Ambil detail kontainer nginx
  -> Kirim pesan: detail nginx + keyboard aksi (Start/Stop/Restart/Logs)
  -> cb_ctx.bot.answer_callback_query(cb_ctx.callback_query_id)

STEP 5: User tekan tombol "Restart" (callback query)
  -> callback_data: "docker_action:restart:nginx"
  -> Auth check: apakah user punya "docker:write"? (OK, admin)
  -> DockerPlugin.handlers.handle_action_confirm(cb_ctx) dipanggil
  -> Edit pesan: "Konfirmasi restart kontainer nginx?" + tombol Ya/Tidak

STEP 6: User tekan "Ya" (callback query)
  -> callback_data: "docker_confirm:restart:nginx:yes"
  -> AuditMiddleware catat: action="docker.restart", target="nginx", status=pending
  -> DockerPlugin.handlers.handle_action_execute(cb_ctx) dipanggil
  -> Edit pesan: "Merestart nginx..."
  -> DockerService.restart_container("nginx")
    -> docker_client.containers.get("nginx").restart()
  -> Edit pesan: "nginx berhasil direstart" + status update
  -> AuditMiddleware update: status=success, duration_ms=1234
  -> EventBus.publish("docker.container_restarted", {container_name: "nginx"})

STEP 7: Event diterima oleh NotificationPlugin
  -> NotificationPlugin.on_container_restarted(payload)
  -> Cek apakah ada alert rule untuk restart events
  -> Jika ada: kirim notifikasi ke admin lain
```

---

## 14. Panduan Membuat Plugin Baru

### Langkah 1: Buat Folder Plugin

```
guardian/plugins/my_plugin/
  __init__.py
  plugin.py
  handlers.py
  service.py
```

### Langkah 2: Definisikan Plugin Class (plugin.py)

```
Struktur minimal plugin.py:

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "Deskripsi plugin saya"
    author = "Nama Saya"
    dependencies = []
    min_core_version = "1.0.0"
    permissions_required = []

    DEFAULT_CONFIG = {}

    async def setup(self, ctx: ApplicationContext) -> None:
        self.service = MyPluginService(ctx)
        self.handlers = MyPluginHandlers(self.service)
        self._register_commands(ctx)
        self._register_events(ctx)

    async def teardown(self) -> None:
        pass

    async def health_check(self) -> PluginHealth:
        return PluginHealth(
            plugin_name=self.name,
            status="healthy",
            message="Plugin berjalan normal",
            checked_at=datetime.now(UTC),
            details={}
        )

    def _register_commands(self, ctx: ApplicationContext) -> None:
        ctx.plugin_manager.register_command(
            namespace=self.name,
            command="hello",
            handler=self.handlers.handle_hello,
            description="Contoh command",
            permissions=["my_plugin:read"]
        )

    def _register_events(self, ctx: ApplicationContext) -> None:
        ctx.event_bus.subscribe("system.startup_complete", self.on_startup)

    async def on_startup(self, payload: dict) -> None:
        self.logger.info("MyPlugin siap")
```

### Langkah 3: Implementasi Handler (handlers.py)

```
Struktur minimal handlers.py:

class MyPluginHandlers:

    def __init__(self, service: MyPluginService) -> None:
        self.service = service

    async def handle_hello(self, cmd_ctx: CommandContext) -> None:
        result = await self.service.get_hello_message()
        await cmd_ctx.bot.send_message(
            chat_id=cmd_ctx.chat_id,
            text=result
        )
```

### Langkah 4: Implementasi Service (service.py)

```
Struktur minimal service.py:

class MyPluginService(BaseService):

    async def get_hello_message(self) -> str:
        return "Halo dari MyPlugin!"

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(status="healthy", message="OK")
```

### Langkah 5: Verifikasi

1. Pastikan tidak ada circular import.
2. Jalankan unit test: `uv run pytest tests/unit/plugins/test_my_plugin.py`.
3. Jalankan bot dalam mode development dan test command `/my_plugin hello`.
4. Verifikasi audit log mencatat tindakan dengan benar.

---

## 15. Plugin Bawaan (Built-in Plugins)

Plugin berikut adalah bagian dari inti distribusi Serverinka Guardian dan selalu dimuat (kecuali dikonfigurasi sebaliknya):

| Nama Plugin | Namespace | Deskripsi |
|-------------|-----------|-----------|
| `system` | `system` | Monitor CPU, RAM, Disk, Network, proses |
| `service_manager` | `service` | Manajemen layanan systemd |
| `docker` | `docker` | Manajemen kontainer Docker |
| `notification` | `alert` | Konfigurasi dan pengiriman alert |
| `scheduler_ui` | `schedule` | UI untuk manajemen jadwal |
| `user_manager` | `user` | Manajemen pengguna bot |
| `audit_viewer` | `audit` | Tampilkan audit log |
| `settings` | `settings` | Konfigurasi bot melalui Telegram |

---

## 16. Keputusan Desain

### Mengapa Discovery Otomatis, Bukan Registrasi Manual?

Registrasi manual (mendaftarkan plugin di file konfigurasi atau kode inti) menambah langkah dan kemungkinan human error. Discovery otomatis lebih mudah: taruh folder plugin di tempat yang benar, dan plugin otomatis dimuat. Kontributor tidak perlu memodifikasi kode inti.

### Mengapa Event Bus, Bukan Direct Import Antar-Plugin?

Direct import antar-plugin menciptakan coupling yang sulit di-maintain. Jika plugin A mengimport plugin B, dan plugin B dinonaktifkan, plugin A akan crash. Event Bus memungkinkan plugin berjalan secara mandiri dan hanya berkomunikasi melalui event yang terdefinisi dengan jelas.

### Mengapa Satu File `plugin.py` per Plugin?

Semua plugin memiliki entrypoint yang konsisten di `plugin.py`. Plugin Manager tidak perlu menebak di mana class plugin berada. Konsistensi ini sangat penting untuk ekosistem plugin komunitas.

### Mengapa Dependency Graph, Bukan Urutan Alphabet?

Beberapa plugin bergantung pada plugin lain. Nginx plugin mungkin bergantung pada service_manager. Dengan dependency graph, Plugin Manager dapat memastikan service_manager dimuat sebelum nginx, mencegah error saat setup.

---

## 17. Checklist Implementasi

### Core Plugin Infrastructure

- [ ] `BasePlugin` abstract class diimplementasi dengan semua method
- [ ] `PluginManager.discover_plugins()` memindai folder `plugins/`
- [ ] `PluginManager` membangun dependency graph dan mengurutkan loading
- [ ] `PluginManager` mendeteksi circular dependency
- [ ] Plugin yang gagal setup ditandai FAILED tanpa menghentikan bot
- [ ] `PluginManager.register_command()` mendaftarkan handler ke router
- [ ] `PluginManager.register_callback()` mendaftarkan callback handler
- [ ] Plugin Manager unit tests

### Event Bus

- [ ] `EventBus` async publish/subscribe diimplementasi
- [ ] Kegagalan subscriber terisolasi (tidak memblokir publisher)
- [ ] Event Bus unit tests

### Built-in Plugins

- [ ] `SystemPlugin` diimplementasi dan teruji
- [ ] `ServiceManagerPlugin` diimplementasi dan teruji
- [ ] `DockerPlugin` diimplementasi dan teruji
- [ ] `NotificationPlugin` diimplementasi dan teruji
- [ ] `SchedulerUIPlugin` diimplementasi dan teruji
- [ ] `UserManagerPlugin` diimplementasi dan teruji

### Documentation

- [ ] Panduan membuat plugin tersedia di CONTRIBUTING.md
- [ ] Plugin API didokumentasikan lengkap
- [ ] Contoh plugin minimal tersedia di `plugins/example/`

---

*Referensi: [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [05_API_DESIGN.md](05_API_DESIGN.md) | [06_SECURITY.md](06_SECURITY.md) | [10_DEVELOPMENT_RULES.md](10_DEVELOPMENT_RULES.md)*
