# 05 — Desain API Internal
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [07_PLUGIN_SYSTEM.md](07_PLUGIN_SYSTEM.md)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Prinsip Desain API Internal](#2-prinsip-desain-api-internal)
3. [Interface Komponen Inti](#3-interface-komponen-inti)
4. [Plugin API](#4-plugin-api)
5. [Service API](#5-service-api)
6. [Repository API](#6-repository-api)
7. [AI Provider API](#7-ai-provider-api)
8. [Telegram API Wrapper](#8-telegram-api-wrapper)
9. [Docker Wrapper API](#9-docker-wrapper-api)
10. [Event Bus API](#10-event-bus-api)
11. [Struktur Response Standar](#11-struktur-response-standar)
12. [Error Hierarchy](#12-error-hierarchy)
13. [Keputusan Desain](#13-keputusan-desain)
14. [Checklist Implementasi](#14-checklist-implementasi)

---

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan seluruh API internal proyek Serverinka Guardian. API internal adalah kontrak antar-modul yang memastikan konsistensi, testability, dan kemudahan pengembangan. Seluruh interface yang didefinisikan di sini bersifat mengikat dan harus diimplementasi sesuai spesifikasi.

---

## 2. Prinsip Desain API Internal

1. **Type-safe:** Semua parameter dan return value harus memiliki type hint yang lengkap.
2. **Async-first:** Semua method yang melakukan I/O harus `async`.
3. **Immutable data:** Gunakan `dataclass` atau `TypedDict` untuk data transfer, bukan dict biasa.
4. **Explicit over implicit:** Tidak ada magic methods tersembunyi. API harus jelas dari signature-nya.
5. **Fail loudly:** Raise exception yang spesifik, jangan kembalikan None secara diam-diam.
6. **Dependency injection:** Komponen menerima dependensi melalui konstruktor, bukan membuat sendiri.

---

## 3. Interface Komponen Inti

### 3.1 ApplicationContext

Container pusat yang menyimpan semua singleton dan meneruskannya ke plugin melalui dependency injection.

```
ApplicationContext:
  Properties:
    config: GuardianSettings          # Konfigurasi aplikasi
    database: DatabaseManager          # Database connection manager
    event_bus: EventBus                # Async event bus
    scheduler: SchedulerEngine         # Scheduler engine
    bot: BotGateway                   # Telegram bot gateway
    auth: AuthService                  # Authentication service
    plugin_manager: PluginManager      # Plugin manager
```

### 3.2 GuardianSettings (Konfigurasi)

```
GuardianSettings:
  Fields:
    telegram_bot_token: str
    telegram_admin_user_ids: list[int]    # Super admin dari .env
    database_path: str
    log_level: str                         # DEBUG | INFO | WARNING | ERROR
    scheduler_alert_interval_seconds: int  # Default: 60
    rate_limit_commands_per_minute: int    # Default: 30
    rate_limit_window_seconds: int         # Default: 60
    docker_enabled: bool                   # Default: True
    ai_provider: str                       # disabled | openai | gemini | ollama
    ai_api_key: str
    ai_model: str
    backup_enabled: bool                   # Default: True
    backup_retention_days: int             # Default: 7
    webhook_enabled: bool                  # Default: False
    webhook_url: str
    webhook_port: int                      # Default: 8443
```

---

## 4. Plugin API

### 4.1 BasePlugin (Abstract Class)

Semua plugin harus mewarisi `BasePlugin` dan mengimplementasikan method yang diwajibkan.

```
BasePlugin:

  Abstract Properties (wajib diimplementasi):
    name: str                    # Identifier unik: "system", "docker", "nginx"
    version: str                 # Semantic version: "1.0.0"
    description: str             # Deskripsi singkat plugin
    dependencies: list[str]      # Plugin lain yang dibutuhkan: ["system"]

  Lifecycle Methods (override jika diperlukan):
    async setup(ctx: ApplicationContext) -> None
      Dipanggil sekali saat plugin pertama kali dimuat.
      Gunakan untuk registrasi handler dan inisialisasi resource.

    async teardown() -> None
      Dipanggil saat plugin dihentikan.
      Gunakan untuk membersihkan resource.

    async health_check() -> PluginHealth
      Kembalikan status kesehatan plugin.
      Dipanggil oleh sistem monitoring internal.

  Registration Methods (tersedia via ctx):
    register_command(namespace: str, command: str, handler: CommandHandler, permissions: list[str]) -> None
      Daftarkan command handler ke router.

    register_event_handler(event_name: str, handler: EventHandler) -> None
      Daftarkan event handler ke event bus.

    register_scheduled_job(name: str, trigger: Trigger, job_func: Callable) -> None
      Daftarkan scheduled job ke scheduler.
```

### 4.2 PluginMetadata

```
PluginMetadata (dataclass):
  name: str
  version: str
  description: str
  author: str
  dependencies: list[str]
  min_core_version: str
  permissions_required: list[str]
```

### 4.3 PluginHealth

```
PluginHealth (dataclass):
  plugin_name: str
  status: str          # "healthy" | "degraded" | "unhealthy"
  message: str
  checked_at: datetime
  details: dict[str, Any]
```

---

## 5. Service API

Services adalah kelas yang mengenkapsulasi logika bisnis dan interaksi dengan sistem. Semua service mewarisi `BaseService`.

### 5.1 BaseService

```
BaseService:
  Constructor:
    __init__(ctx: ApplicationContext) -> None

  Abstract Methods:
    async health_check() -> ServiceHealth
```

### 5.2 SystemService API

Menyediakan akses ke metrik dan informasi sistem Linux.

```
SystemService(BaseService):

  async get_system_info() -> SystemInfo
    Returns:
      SystemInfo:
        hostname: str
        os_name: str
        os_version: str
        kernel_version: str
        architecture: str
        python_version: str
        uptime_seconds: int
        boot_time: datetime

  async get_cpu_metrics() -> CpuMetrics
    Returns:
      CpuMetrics:
        usage_percent: float           # Overall CPU usage 0-100
        per_core_percent: list[float]  # Per-core usage
        load_average_1m: float
        load_average_5m: float
        load_average_15m: float
        core_count: int
        frequency_mhz: float

  async get_memory_metrics() -> MemoryMetrics
    Returns:
      MemoryMetrics:
        total_bytes: int
        available_bytes: int
        used_bytes: int
        usage_percent: float
        swap_total_bytes: int
        swap_used_bytes: int
        swap_percent: float

  async get_disk_metrics() -> list[DiskMetrics]
    Returns list of:
      DiskMetrics:
        mount_point: str
        device: str
        filesystem: str
        total_bytes: int
        used_bytes: int
        free_bytes: int
        usage_percent: float

  async get_network_metrics() -> list[NetworkMetrics]
    Returns list of:
      NetworkMetrics:
        interface: str
        bytes_sent: int
        bytes_recv: int
        packets_sent: int
        packets_recv: int
        errors_in: int
        errors_out: int

  async get_top_processes(limit: int = 10) -> list[ProcessInfo]
    Returns list of:
      ProcessInfo:
        pid: int
        name: str
        username: str
        cpu_percent: float
        memory_percent: float
        memory_rss_bytes: int
        status: str
        create_time: datetime

  async kill_process(pid: int) -> ProcessKillResult
    Raises:
      PermissionError: jika tidak ada izin untuk kill proses ini
      ProcessNotFoundError: jika PID tidak ditemukan
    Returns:
      ProcessKillResult:
        success: bool
        pid: int
        message: str

  async run_system_update() -> AsyncGenerator[str, None]
    Yields output baris demi baris dari apt update && apt upgrade
    Raises:
      CommandExecutionError: jika perintah gagal
```

### 5.3 ServiceManagerService API

Berinteraksi dengan systemd untuk manajemen layanan.

```
ServiceManagerService(BaseService):

  async list_services(filter_active: bool = False) -> list[ServiceInfo]
    Returns list of:
      ServiceInfo:
        name: str
        description: str
        load_state: str       # loaded | not-found | masked
        active_state: str     # active | inactive | failed | activating
        sub_state: str        # running | dead | exited
        is_enabled: bool
        main_pid: int | None

  async get_service_status(service_name: str) -> ServiceStatus
    Raises:
      ServiceNotFoundError
    Returns:
      ServiceStatus:
        name: str
        active_state: str
        sub_state: str
        is_enabled: bool
        main_pid: int | None
        memory_bytes: int | None
        cpu_percent: float | None
        runtime_seconds: int | None
        recent_logs: list[str]

  async start_service(service_name: str) -> ServiceOperationResult
  async stop_service(service_name: str) -> ServiceOperationResult
  async restart_service(service_name: str) -> ServiceOperationResult
  async enable_service(service_name: str) -> ServiceOperationResult
  async disable_service(service_name: str) -> ServiceOperationResult
    Raises:
      ServiceNotFoundError
      ServiceOperationError
    Returns:
      ServiceOperationResult:
        success: bool
        service_name: str
        operation: str
        new_state: str
        message: str

  async get_service_logs(service_name: str, lines: int = 50) -> list[str]
    Raises:
      ServiceNotFoundError
```

### 5.4 DockerService API

Berinteraksi dengan Docker Engine melalui Docker SDK.

```
DockerService(BaseService):

  async is_available() -> bool
    Cek apakah Docker Engine dapat diakses.

  async list_containers(all: bool = True) -> list[ContainerInfo]
    Returns list of:
      ContainerInfo:
        id: str
        short_id: str
        name: str
        image: str
        status: str           # running | exited | paused | restarting
        state: str
        created_at: datetime
        ports: dict[str, Any]
        labels: dict[str, str]

  async start_container(container_id: str) -> ContainerOperationResult
  async stop_container(container_id: str) -> ContainerOperationResult
  async restart_container(container_id: str) -> ContainerOperationResult
    Raises:
      ContainerNotFoundError
      DockerOperationError
    Returns:
      ContainerOperationResult:
        success: bool
        container_id: str
        container_name: str
        operation: str
        message: str

  async get_container_logs(container_id: str, tail: int = 100) -> list[str]

  async get_container_stats(container_id: str) -> ContainerStats
    Returns:
      ContainerStats:
        container_id: str
        container_name: str
        cpu_percent: float
        memory_usage_bytes: int
        memory_limit_bytes: int
        memory_percent: float
        network_rx_bytes: int
        network_tx_bytes: int

  async list_images() -> list[ImageInfo]
    Returns list of:
      ImageInfo:
        id: str
        tags: list[str]
        size_bytes: int
        created_at: datetime

  async pull_image(image_name: str) -> AsyncGenerator[str, None]
    Yields progress output

  async remove_image(image_id: str, force: bool = False) -> bool
```

### 5.5 AuthService API

```
AuthService(BaseService):

  async authenticate(telegram_id: int, username: str, full_name: str) -> AuthResult
    Cek apakah user terdaftar dan aktif.
    Returns:
      AuthResult:
        is_authorized: bool
        user: UserDTO | None
        denial_reason: str | None

  async get_user(telegram_id: int) -> UserDTO | None

  async has_permission(telegram_id: int, permission: str) -> bool
    Cek apakah user memiliki permission untuk tindakan tertentu.

  async add_user(telegram_id: int, username: str, full_name: str, role: str, added_by: int) -> UserDTO
    Raises:
      UserAlreadyExistsError
      InvalidRoleError

  async update_user_role(telegram_id: int, new_role: str, updated_by: int) -> UserDTO
    Raises:
      UserNotFoundError
      InvalidRoleError
      PermissionDeniedError  # Tidak bisa ubah super_admin

  async deactivate_user(telegram_id: int, deactivated_by: int) -> bool
  async block_user(telegram_id: int, blocked_by: int) -> bool
```

---

## 6. Repository API

Repository adalah lapisan akses data. Semua Repository mewarisi `BaseRepository`.

### 6.1 BaseRepository

```
BaseRepository:
  Constructor:
    __init__(db: DatabaseManager) -> None
```

### 6.2 UserRepository

```
UserRepository(BaseRepository):

  async find_by_telegram_id(telegram_id: int) -> UserDTO | None
  async find_by_id(user_id: int) -> UserDTO | None
  async find_all_active() -> list[UserDTO]
  async find_alert_recipients() -> list[int]  # list telegram_id
  async create(telegram_id, username, full_name, role, added_by) -> UserDTO
  async update_role(user_id, new_role) -> UserDTO
  async update_activity(telegram_id, username, full_name) -> None
  async deactivate(user_id) -> bool
  async block(user_id) -> bool
```

### 6.3 AuditLogRepository

```
AuditLogRepository(BaseRepository):

  async create(user_id, telegram_id, action, target, parameters) -> int
    Returns: ID record yang baru dibuat

  async update_result(log_id, result_status, error_message, duration_ms) -> None

  async find_by_user(user_id, limit, offset) -> list[AuditLogDTO]
  async find_by_action(action, limit, offset) -> list[AuditLogDTO]
  async find_recent(limit) -> list[AuditLogDTO]
  async count_by_user(user_id, since_datetime) -> int
    Digunakan oleh rate limiter
```

---

## 7. AI Provider API

AI Gateway menyediakan abstraksi di atas berbagai AI provider.

### 7.1 BaseAIProvider

```
BaseAIProvider:

  Abstract Methods:
    async complete(prompt: str, context: str, max_tokens: int) -> AIResponse
    async analyze_logs(logs: list[str], query: str) -> AIResponse

  Returns:
    AIResponse (dataclass):
      content: str
      provider: str
      model: str
      tokens_used: int
      duration_ms: int
```

### 7.2 AIGateway

```
AIGateway:

  Constructor:
    __init__(config: GuardianSettings) -> None

  Method:
    get_provider() -> BaseAIProvider | None
      Kembalikan provider yang dikonfigurasi, atau None jika AI disabled.

    async analyze_logs(logs: list[str], query: str) -> str
      Shorthand untuk analisis log. Kembalikan respons teks.
      Raises:
        AIProviderNotConfiguredError
        AIProviderError
```

---

## 8. Telegram API Wrapper

### 8.1 BotGateway

```
BotGateway:

  async send_message(
      chat_id: int,
      text: str,
      keyboard: InlineKeyboard | None = None,
      parse_mode: str = "HTML"
  ) -> Message

  async send_long_message(
      chat_id: int,
      text: str,
      keyboard: InlineKeyboard | None = None
  ) -> list[Message]
    Otomatis split pesan yang melebihi 4096 karakter.

  async edit_message(
      chat_id: int,
      message_id: int,
      text: str,
      keyboard: InlineKeyboard | None = None
  ) -> Message

  async answer_callback_query(
      callback_query_id: str,
      text: str = "",
      show_alert: bool = False
  ) -> None

  async send_document(
      chat_id: int,
      document: bytes | str,
      filename: str,
      caption: str = ""
  ) -> Message

  async broadcast(
      user_ids: list[int],
      text: str,
      keyboard: InlineKeyboard | None = None
  ) -> BroadcastResult
    Returns:
      BroadcastResult:
        sent_count: int
        failed_count: int
        failed_user_ids: list[int]
```

### 8.2 CommandContext

Objek yang diteruskan ke setiap command handler berisi semua informasi yang diperlukan.

```
CommandContext (dataclass):
  user: UserDTO               # User yang mengirim perintah
  chat_id: int                # Chat ID tujuan respons
  message_id: int             # ID pesan original
  command: str                # Nama command: "list", "start", dll
  args: list[str]             # Argumen command
  raw_text: str               # Teks pesan original
  update: Update              # Telegram Update object asli
  bot: BotGateway             # Shortcut ke bot gateway
  ctx: ApplicationContext     # Akses ke semua komponen
```

### 8.3 CallbackContext

Objek yang diteruskan ke callback query handler (inline keyboard button press).

```
CallbackContext (dataclass):
  user: UserDTO
  chat_id: int
  message_id: int
  callback_query_id: str
  data: str                   # Callback data dari button
  parsed_data: dict[str, Any] # Data yang sudah di-parse dari JSON
  bot: BotGateway
  ctx: ApplicationContext
```

---

## 9. Docker Wrapper API

Abstraksi tambahan di atas docker-py SDK untuk memudahkan error handling dan testing.

```
DockerClientWrapper:

  async get_client() -> docker.DockerClient
    Raises:
      DockerNotAvailableError: jika Docker socket tidak dapat diakses

  async execute_with_retry(operation: Callable, max_retries: int = 2) -> Any
    Wrapper untuk menangani transient Docker API errors.
```

---

## 10. Event Bus API

### 10.1 EventBus

```
EventBus:

  async publish(event_name: str, payload: dict[str, Any]) -> None
    Kirim event ke semua subscriber secara async.
    Error pada subscriber tidak memblokir publisher atau subscriber lain.

  def subscribe(event_name: str, handler: EventHandler) -> None
    Daftarkan handler untuk event tertentu.
    Handler harus async: async def handler(payload: dict) -> None

  def unsubscribe(event_name: str, handler: EventHandler) -> None
    Hapus handler dari subscriber list.
```

### 10.2 Event Names yang Didefinisikan

```
System Events:
  "system.startup_complete"       # Bot selesai startup
  "system.shutdown_requested"     # Shutdown diminta
  "system.plugin_loaded"          # Plugin berhasil dimuat
  "system.plugin_error"           # Plugin mengalami error

Auth Events:
  "auth.user_authenticated"       # User berhasil terautentikasi
  "auth.user_denied"              # Akses user ditolak
  "auth.user_blocked"             # User diblokir

Alert Events:
  "alert.threshold_exceeded"      # Metrik melewati threshold
  "alert.service_down"            # Layanan systemd crash

Docker Events:
  "docker.container_started"
  "docker.container_stopped"
  "docker.container_restarted"

Service Events:
  "service.started"
  "service.stopped"
  "service.restarted"
  "service.failed"
```

---

## 11. Struktur Response Standar

### 11.1 ServiceResult

Semua operasi service yang dapat berhasil atau gagal mengembalikan `ServiceResult`.

```
ServiceResult (dataclass, generic: T):
  success: bool
  data: T | None
  error: ServiceError | None
  duration_ms: int
```

### 11.2 ServiceError

```
ServiceError (dataclass):
  code: str         # ERROR_CODE_FORMAT: "DOCKER_NOT_AVAILABLE"
  message: str      # Pesan error yang ramah pengguna (bahasa Indonesia)
  detail: str       # Detail teknis untuk logging
```

### 11.3 Pagination

Untuk semua API yang mengembalikan list:

```
PaginatedResult (dataclass, generic: T):
  items: list[T]
  total: int
  page: int
  page_size: int
  has_next: bool
  has_prev: bool
```

### 11.4 UserDTO

```
UserDTO (dataclass):
  id: int
  telegram_id: int
  username: str | None
  full_name: str
  role: str             # "super_admin" | "admin" | "operator" | "viewer"
  is_active: bool
  is_blocked: bool
  alert_enabled: bool
  created_at: datetime
```

---

## 12. Error Hierarchy

```
GuardianBaseError
  |
  +-- AuthError
  |     +-- UserNotFoundError
  |     +-- UserAlreadyExistsError
  |     +-- InvalidRoleError
  |     +-- PermissionDeniedError
  |     +-- UserBlockedError
  |     +-- UserInactiveError
  |
  +-- PluginError
  |     +-- PluginNotFoundError
  |     +-- PluginLoadError
  |     +-- PluginDependencyError
  |     +-- PluginAlreadyRegisteredError
  |
  +-- ServiceError
  |     +-- ServiceNotFoundError      # systemd service tidak ditemukan
  |     +-- ServiceOperationError     # systemctl gagal
  |     +-- ProcessNotFoundError      # PID tidak ditemukan
  |     +-- CommandExecutionError     # subprocess gagal
  |
  +-- DockerError
  |     +-- DockerNotAvailableError   # Docker daemon tidak jalan
  |     +-- ContainerNotFoundError    # Kontainer tidak ditemukan
  |     +-- DockerOperationError      # Operasi Docker gagal
  |
  +-- DatabaseError
  |     +-- MigrationError
  |     +-- QueryError
  |
  +-- ConfigError
  |     +-- MissingConfigError        # Konfigurasi wajib tidak ada
  |     +-- InvalidConfigError        # Nilai konfigurasi tidak valid
  |
  +-- AIError
  |     +-- AIProviderNotConfiguredError
  |     +-- AIProviderError           # API call gagal
  |
  +-- SchedulerError
  |     +-- JobNotFoundError
  |     +-- InvalidCronExpressionError
  |
  +-- RateLimitError                  # User terlalu banyak request
```

---

## 13. Keputusan Desain

### Mengapa Menggunakan Dataclass, Bukan TypedDict atau Dict Biasa?

Dataclass memberikan type safety yang penuh, validasi di level IDE, dan dapat ditambahkan metode. TypedDict hanya untuk type checking, tidak ada runtime enforcement. Dict biasa tidak memiliki type safety sama sekali.

### Mengapa `CommandContext` dan `CallbackContext` Terpisah?

Command dan callback memiliki data yang berbeda. Menyatukan keduanya dalam satu class akan menghasilkan banyak field opsional (None) yang membingungkan dan rawan bug. Pemisahan ini mengikuti prinsip Interface Segregation.

### Mengapa `ServiceResult[T]` sebagai Return Type?

Ini memungkinkan caller untuk menangani success dan error secara eksplisit tanpa try-catch di setiap pemanggil. Namun, untuk error yang benar-benar tidak diharapkan (bug, bukan expected error), exception tetap harus di-raise.

### Mengapa Event Bus Menggunakan String sebagai Event Name?

String event name sederhana, tidak memerlukan import class event, dan mudah di-extend. Untuk menghindari typo, semua event name didefinisikan sebagai konstanta di modul `core/events.py`.

---

## 14. Checklist Implementasi

### Interface & Abstract Classes

- [ ] Implementasi `BasePlugin` dengan semua abstract method
- [ ] Implementasi `BaseService` dengan `health_check`
- [ ] Implementasi `BaseRepository` dengan connection injection
- [ ] Semua dataclass (ServiceResult, UserDTO, dll) diimplementasi

### Services

- [ ] `SystemService` dengan semua method dan unit test
- [ ] `ServiceManagerService` dengan semua method dan unit test
- [ ] `DockerService` dengan semua method dan unit test (mocked)
- [ ] `AuthService` dengan semua method dan unit test

### Bot Infrastructure

- [ ] `BotGateway` dengan semua method
- [ ] `CommandContext` dan `CallbackContext` diimplementasi
- [ ] Command router yang menangani namespace "plugin.command"

### Error Handling

- [ ] Semua custom exception class diimplementasi di `core/exceptions.py`
- [ ] Global error handler di bot gateway
- [ ] Error logging yang konsisten

---

*Referensi: [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) | [04_DATABASE_DESIGN.md](04_DATABASE_DESIGN.md) | [06_SECURITY.md](06_SECURITY.md) | [07_PLUGIN_SYSTEM.md](07_PLUGIN_SYSTEM.md)*
