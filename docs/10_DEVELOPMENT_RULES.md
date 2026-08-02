# 10 — Aturan Pengembangan
# Serverinka Guardian

> **Versi Dokumen:** 1.0.0
> **Tanggal:** 2026-08-02
> **Status:** Disetujui — Fondasi Proyek — MENGIKAT
> **Penulis:** Tim Arsitektur Serverinka Guardian
> **Referensi:** Seluruh dokumen teknis (01–09)

---

## Daftar Isi

1. [Tujuan Dokumen](#1-tujuan-dokumen)
2. [Coding Standard](#2-coding-standard)
3. [Naming Convention](#3-naming-convention)
4. [Folder & File Convention](#4-folder--file-convention)
5. [Architecture Rule](#5-architecture-rule)
6. [Import Rule](#6-import-rule)
7. [Type Hint Rule](#7-type-hint-rule)
8. [Async Rule](#8-async-rule)
9. [Error Handling Rule](#9-error-handling-rule)
10. [Dependency Rule](#10-dependency-rule)
11. [Plugin Rule](#11-plugin-rule)
12. [Testing Rule](#12-testing-rule)
13. [Branching Strategy](#13-branching-strategy)
14. [Commit Convention](#14-commit-convention)
15. [Release Rule](#15-release-rule)
16. [Quality Checklist](#16-quality-checklist)
17. [Keputusan Desain](#17-keputusan-desain)

---

## 1. Tujuan Dokumen

Dokumen ini adalah **hukum tertinggi pengembangan** Serverinka Guardian. Setiap baris kode, setiap commit, dan setiap kontribusi harus mengikuti aturan di dokumen ini. Aturan ini ada untuk memastikan kode tetap bersih, aman, mudah dipahami, dan dapat dikembangkan bertahun-tahun.

**Tidak ada pengecualian tanpa diskusi dan dokumentasi yang jelas.**

---

## 2. Coding Standard

### 2.1 Versi Python

```
Minimum: Python 3.12
Dilarang: Fitur yang tidak tersedia di Python 3.12
```

### 2.2 Panjang File

```
ATURAN KERAS: Tidak ada file Python yang melebihi 500 baris.

Jika sebuah file mendekati 400 baris, ini adalah sinyal bahwa modul
harus dipecah menjadi beberapa file yang lebih fokus.

Pengecualian: File test boleh lebih panjang jika test case-nya lengkap
dan tidak ada cara memisahkan secara logis. Maksimum: 700 baris.
```

### 2.3 Panjang Baris

```
Maksimum 100 karakter per baris.
Dikonfigurasi di pyproject.toml [tool.ruff] line-length = 100
```

### 2.4 Komentar

```
ATURAN: Jangan menulis komentar yang menjelaskan APA yang dilakukan kode.
Kode yang baik cukup jelas dari nama variabel, fungsi, dan strukturnya.

BOLEH:
  - Komentar yang menjelaskan MENGAPA keputusan teknis tertentu dibuat.
  - Komentar yang menjelaskan workaround untuk bug library pihak ketiga.
  - Docstring untuk modul, class, dan fungsi publik.
  - TODO / FIXME dengan isi yang jelas dan dapat dilacak.

DILARANG:
  - Komentar yang hanya mengulang nama fungsi atau variabel.
  - Komentar yang sudah tidak relevan dengan kode saat ini.
  - Komentar yang menerangkan hal yang sudah jelas dari nama fungsi.
  - Komentar yang di-comment-out sebagai backup kode lama.
```

**Contoh Benar:**
```
# Telegram API rate limit: maksimal 30 pesan per detik ke chat yang berbeda
TELEGRAM_MAX_MESSAGES_PER_SECOND = 30

# Gunakan VACUUM INTO bukan BACKUP API karena WAL mode yang aktif
# Referensi: https://www.sqlite.org/lang_vacuum.html
```

**Contoh Salah:**
```
# Loop through containers
for container in containers:
    # Call restart method
    await container.restart()
```

### 2.5 Docstring

```
Gunakan Google-style docstring untuk semua class dan fungsi publik.
Fungsi private (diawali _) tidak wajib docstring jika nama sudah jelas.

Format:
  def function_name(param: type) -> return_type:
      """Ringkasan satu baris.

      Penjelasan lebih detail jika diperlukan.

      Args:
          param: Deskripsi parameter.

      Returns:
          Deskripsi return value.

      Raises:
          ExceptionType: Kondisi yang menyebabkan exception.
      """
```

---

## 3. Naming Convention

### 3.1 Python Naming

| Entitas | Convention | Contoh |
|---------|------------|--------|
| Module/File | snake_case | `plugin_manager.py`, `auth_service.py` |
| Package/Folder | snake_case | `core/`, `service_manager/` |
| Class | PascalCase | `PluginManager`, `AuthService` |
| Function/Method | snake_case | `get_container_stats()`, `authenticate()` |
| Variable | snake_case | `user_count`, `container_name` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Private method | _snake_case | `_load_plugin()`, `_validate_input()` |
| Protected method | _snake_case | `_register_handlers()` |
| Type alias | PascalCase | `ContainerList`, `UserId` |
| Dataclass | PascalCase | `UserDTO`, `ContainerInfo` |
| Abstract class | PascalCase | `BasePlugin`, `BaseService` |
| Exception class | PascalCase + Error | `AuthError`, `DockerNotAvailableError` |

### 3.2 Aturan Penamaan Spesifik

```
Plugin:
  - Nama direktori: snake_case, sama dengan namespace command.
  - Nama class plugin: {Name}Plugin
  - Nama file entrypoint: plugin.py (selalu)

Service:
  - Nama class: {Name}Service
  - Nama file: service.py

Repository:
  - Nama class: {Name}Repository
  - Nama file: repository.py

Handler:
  - Nama class: {Name}Handlers atau {Name}Handler
  - Nama file: handlers.py
  - Nama method: handle_{action} (contoh: handle_list, handle_restart)

Test:
  - Nama file: test_{module_name}.py
  - Nama class: Test{ClassName}
  - Nama method: test_{scenario}_{expected_result}
    Contoh: test_authenticate_with_unknown_user_returns_denied
```

### 3.3 Aturan Nama yang Jelas

```
GUNAKAN nama yang deskriptif dan jelas:

  BENAR: user_telegram_id, container_name, is_service_active
  SALAH: uid, cn, active

  BENAR: async def restart_container(container_name: str) -> ContainerOperationResult:
  SALAH: async def do_thing(name: str) -> dict:

  BENAR: MAX_ALERT_COOLDOWN_MINUTES = 30
  SALAH: MCM = 30

  BENAR: for user in active_users:
  SALAH: for u in users:
```

---

## 4. Folder & File Convention

### 4.1 Satu Tanggung Jawab per File

Setiap file Python memiliki SATU tanggung jawab yang jelas:

| File | Tanggung Jawab |
|------|----------------|
| `plugin.py` | Definisi plugin, lifecycle, registrasi |
| `handlers.py` | Command dan callback handler Telegram |
| `service.py` | Logika bisnis, interaksi dengan sistem |
| `repository.py` | Akses data, query SQL |
| `models.py` | Dataclass, TypedDict, type aliases |
| `validators.py` | Validasi input |
| `keyboards.py` | Definisi inline keyboard |
| `messages.py` | Template teks pesan |
| `exceptions.py` | Custom exception classes |

### 4.2 Tidak Boleh Ada File Tanpa Home

Setiap file harus jelas masuk ke kategori mana. Jika tidak jelas, ini sinyal bahwa struktur perlu dipertimbangkan ulang.

### 4.3 Test File Mirroring

Struktur folder test mencerminkan struktur folder sumber:

```
guardian/core/auth_service.py
  -> tests/unit/core/test_auth_service.py

guardian/plugins/docker/service.py
  -> tests/unit/plugins/docker/test_service.py
```

---

## 5. Architecture Rule

### 5.1 Layered Architecture Enforcement

```
ATURAN KETERGANTUNGAN LAPISAN:
Lapisan atas boleh bergantung pada lapisan bawah.
Lapisan bawah TIDAK BOLEH bergantung pada lapisan atas.

Presentation (bot_gateway, handlers)
  |-- bergantung pada -->
Application (plugin_manager, auth_service, scheduler)
  |-- bergantung pada -->
Domain (business logic dalam service.py dan handler logic)
  |-- bergantung pada -->
Infrastructure (database.py, docker SDK, subprocess)
  |-- bergantung pada -->
External (Telegram API, Docker Engine, Linux OS)
```

### 5.2 Dependency Injection Wajib

```
DILARANG membuat instance dependensi di dalam class secara langsung.

SALAH:
  class DockerPlugin(BasePlugin):
      def __init__(self):
          self.db = DatabaseManager()  # SALAH: membuat sendiri
          self.service = DockerService()  # SALAH

BENAR:
  class DockerPlugin(BasePlugin):
      async def setup(self, ctx: ApplicationContext) -> None:
          self.service = DockerService(ctx)  # ctx diinjeksi dari luar
```

### 5.3 Single Responsibility Principle

```
Setiap class/modul harus memiliki SATU alasan untuk berubah.

Tanda bahwa SRP dilanggar:
  - Class/file memiliki lebih dari satu "peran" (handler DAN service)
  - Method melakukan lebih dari satu level abstraksi
  - File melebihi 300-400 baris

Ketika menemukan ini: REFAKTOR segera.
```

### 5.4 Open/Closed Principle untuk Plugin

```
Core engine harus TERTUTUP untuk modifikasi dan TERBUKA untuk ekstensi.

DILARANG: Menambahkan logika plugin ke dalam core engine.
BENAR: Menambahkan plugin baru ke folder plugins/.

Setiap kali ingin menambahkan fitur: buat plugin baru.
Jangan modifikasi plugin_manager.py untuk fitur spesifik plugin.
```

---

## 6. Import Rule

### 6.1 Urutan Import

Ikuti urutan standar Python (diatur oleh Ruff/isort):

```
1. Standard library imports
   import os
   import asyncio
   from datetime import datetime

2. Third-party imports
   import aiosqlite
   from telegram import Update

3. Local imports (absolute)
   from guardian.core.config import GuardianSettings
   from guardian.interfaces.base_plugin import BasePlugin

4. Local imports (relative) - OPSIONAL untuk modul dalam package yang sama
   from .service import DockerService
   from .models import ContainerInfo
```

### 6.2 No Circular Imports

```
ATURAN KERAS: Tidak ada circular import.

Circular import adalah ketika modul A mengimport modul B,
dan modul B mengimport modul A (langsung atau tidak langsung).

Cara mencegah:
  - Gunakan dependency injection alih-alih direct import
  - Plugin tidak boleh saling mengimport
  - Gunakan Event Bus untuk komunikasi antar-plugin
  - Letakkan shared types/models di guardian/interfaces/ atau guardian/utils/

Cara deteksi:
  - uv run mypy . akan melaporkan circular import
  - ImportError: cannot import name X (jika tidak terdeteksi mypy)
```

### 6.3 No Wildcard Import

```
DILARANG:
  from guardian.core import *
  from .models import *

BENAR:
  from guardian.core.config import GuardianSettings
  from .models import ContainerInfo, ContainerStats
```

### 6.4 Lazy Import untuk Opsional Dependencies

```
Dependensi yang opsional (docker, cloudflare, dll) harus diimport
dengan lazy loading dan ditangani jika tidak tersedia:

  try:
      import docker
      DOCKER_AVAILABLE = True
  except ImportError:
      DOCKER_AVAILABLE = False
```

---

## 7. Type Hint Rule

### 7.1 Type Hint Wajib untuk Semua Fungsi

```
ATURAN KERAS: Semua parameter dan return type WAJIB diberi type hint.

SALAH:
  def get_user(telegram_id):
      ...

  async def restart_container(name, force=False):
      ...

BENAR:
  def get_user(telegram_id: int) -> UserDTO | None:
      ...

  async def restart_container(name: str, force: bool = False) -> ContainerOperationResult:
      ...
```

### 7.2 Penggunaan Type Annotation Modern (Python 3.12+)

```
GUNAKAN syntax modern:
  BENAR:  str | None              (bukan Optional[str])
  BENAR:  list[str]               (bukan List[str])
  BENAR:  dict[str, int]          (bukan Dict[str, int])
  BENAR:  tuple[str, ...]         (bukan Tuple[str, ...])

Masih valid untuk kasus kompleks:
  from typing import TypeVar, Generic, Callable, Awaitable
```

### 7.3 Generic Types

```
Gunakan TypeVar dan Generic untuk fungsi dan class yang generic:

  T = TypeVar("T")

  class PaginatedResult(Generic[T]):
      items: list[T]
      total: int
      ...
```

### 7.4 Mypy Strict Mode

```
Semua kode harus lulus mypy dengan konfigurasi strict:
  [tool.mypy]
  strict = true
  python_version = "3.12"
  
Cara verifikasi:
  uv run mypy .
```

---

## 8. Async Rule

### 8.1 Async untuk Semua I/O

```
ATURAN KERAS: Semua operasi I/O WAJIB menggunakan async/await.

I/O operations:
  - Database query: gunakan aiosqlite, bukan sqlite3
  - HTTP request: gunakan httpx (async client), bukan requests
  - File I/O: gunakan aiofiles untuk file besar, atau asyncio.to_thread untuk kecil
  - subprocess: gunakan asyncio.create_subprocess_exec
  - Docker API: gunakan docker-py dalam asyncio.to_thread (docker-py belum async)
  - Sleep/delay: gunakan asyncio.sleep, bukan time.sleep
```

### 8.2 Tidak Boleh Blokir Event Loop

```
DILARANG: Operasi blocking dalam async function tanpa wrapper.

SALAH:
  async def get_stats():
      time.sleep(1)          # MEMBLOKIR event loop!
      result = requests.get("...")  # MEMBLOKIR event loop!

BENAR:
  async def get_stats():
      await asyncio.sleep(1)
      async with httpx.AsyncClient() as client:
          result = await client.get("...")

Untuk operasi sync yang tidak bisa diubah (misal: psutil):
  async def get_cpu_metrics():
      loop = asyncio.get_event_loop()
      return await loop.run_in_executor(None, psutil.cpu_percent, 1)
      
  Atau gunakan asyncio.to_thread (Python 3.9+):
      return await asyncio.to_thread(psutil.cpu_percent, 1)
```

### 8.3 Timeout untuk Semua Async I/O

```
Semua operasi async yang berinteraksi dengan sistem eksternal harus memiliki timeout:

  async with asyncio.timeout(10):  # timeout 10 detik
      result = await service.get_container_stats(container_id)

  Gunakan asyncio.wait_for sebagai alternatif:
  result = await asyncio.wait_for(
      service.get_container_stats(container_id),
      timeout=10.0
  )
```

### 8.4 TaskGroup untuk Concurrent Operations

```
Gunakan asyncio.TaskGroup untuk operasi concurrent yang harus selesai semua:

  async with asyncio.TaskGroup() as tg:
      cpu_task = tg.create_task(service.get_cpu_metrics())
      ram_task = tg.create_task(service.get_memory_metrics())
      disk_task = tg.create_task(service.get_disk_metrics())
  
  # Semua task selesai di sini
  cpu = cpu_task.result()
  ram = ram_task.result()
  disk = disk_task.result()
```

---

## 9. Error Handling Rule

### 9.1 Raise Specific Exception

```
ATURAN: Gunakan exception yang spesifik dan bermakna.

SALAH:
  raise Exception("Something went wrong")
  raise ValueError("Error")

BENAR:
  raise ServiceNotFoundError(f"Layanan '{service_name}' tidak ditemukan")
  raise DockerNotAvailableError("Docker daemon tidak dapat diakses via socket")
  raise PermissionDeniedError(
      f"User {user_id} tidak memiliki izin untuk {permission}"
  )
```

### 9.2 Tidak Ada Silent Exception

```
DILARANG: Meng-catch exception dan mengabaikannya secara diam-diam.

SALAH:
  try:
      result = await service.do_something()
  except Exception:
      pass  # SANGAT SALAH

BENAR:
  try:
      result = await service.do_something()
  except SpecificError as e:
      logger.error("Gagal melakukan sesuatu", error=str(e))
      raise  # re-raise jika perlu
      # ATAU handle dengan benar:
      return ServiceResult(success=False, error=ServiceError(message=str(e)))
```

### 9.3 Catch yang Spesifik, Bukan Exception Umum

```
SALAH:
  try:
      await docker_service.restart_container(name)
  except Exception as e:
      await ctx.bot.send_message(chat_id, f"Error: {e}")

BENAR:
  try:
      await docker_service.restart_container(name)
  except ContainerNotFoundError:
      await ctx.bot.send_message(chat_id, f"Kontainer '{name}' tidak ditemukan.")
  except DockerOperationError as e:
      await ctx.bot.send_message(chat_id, f"Gagal restart kontainer: {e.message}")
      logger.error("Docker restart failed", container=name, error=str(e))
```

### 9.4 Global Error Handler sebagai Safety Net

```
Global error handler di BotGateway menangkap exception yang tidak tertangani
dari handler plugin. Ini adalah SAFETY NET, bukan pengganti error handling yang benar.

Jika global handler terpicu: ini WAJIB dianggap sebagai bug dan diperbaiki.
```

### 9.5 Exception Logging

```
Semua exception yang dicatch harus di-log dengan context yang cukup:

  logger.error(
      "Gagal merestart kontainer",
      container_name=name,
      user_id=cmd_ctx.user.telegram_id,
      error=str(e),
      exc_info=True  # Sertakan stack trace di DEBUG mode
  )
```

---

## 10. Dependency Rule

### 10.1 Dependency Eksternal

```
Aturan untuk menambahkan dependency baru:
  1. Diskusikan kebutuhan: apakah benar-benar perlu?
  2. Cek apakah stdlib sudah cukup
  3. Pilih library yang aktif dikembangkan dan memiliki test yang baik
  4. Tambahkan ke pyproject.toml dengan version constraint yang tepat
  5. Update uv.lock dengan uv lock
  6. Dokumentasikan MENGAPA dependency ini ditambahkan di pyproject.toml
```

### 10.2 Version Pinning Strategy

```
Gunakan range yang reasonable, bukan pin ke versi exact:

  BENAR:   "httpx>=0.27.0,<1.0.0"   <- Pin ke major version
  BENAR:   "psutil>=6.0.0"          <- Minimum version
  SALAH:   "httpx==0.27.3"          <- Terlalu ketat, sulit update
  SALAH:   "httpx"                  <- Tidak ada constraint

Untuk dependency kritis (telegram bot): lebih ketat:
  "python-telegram-bot>=21.0,<22.0"
```

### 10.3 No Hardcoded Configuration

```
ATURAN KERAS: Tidak ada konfigurasi yang di-hardcode dalam kode.

SALAH:
  BOT_TOKEN = "1234567890:ABCdef..."  # SANGAT BERBAHAYA
  DATABASE_PATH = "/home/user/guardian.db"  # Hardcode path
  ADMIN_ID = 123456789  # Hardcode admin ID

BENAR:
  settings = get_settings()  # Dari environment variable via GuardianSettings
  bot_token = settings.telegram_bot_token
  db_path = settings.database_path
  admin_ids = settings.telegram_admin_user_ids
```

---

## 11. Plugin Rule

### 11.1 Plugin Tidak Boleh Mengimport Plugin Lain

```
DILARANG:
  # Di dalam plugins/nginx/service.py
  from guardian.plugins.service_manager.service import ServiceManagerService  # SALAH

BENAR:
  # Gunakan event bus untuk komunikasi antar-plugin
  await ctx.event_bus.publish("service.restart_requested", {...})
  
  # Atau jika benar-benar perlu data dari plugin lain, gunakan shared service
  # melalui ApplicationContext
```

### 11.2 Plugin Wajib Menangani Kegagalan Gracefully

```
Plugin yang gagal TIDAK BOLEH menghentikan bot.

setup() wajib menangkap dependency errors:
  async def setup(self, ctx: ApplicationContext) -> None:
      try:
          await self._check_prerequisites()
          self._register_commands(ctx)
      except PrerequisiteNotAvailableError as e:
          raise PluginSetupError(f"Plugin {self.name} tidak dapat dimuat: {e}") from e
```

### 11.3 Plugin Wajib Mendefinisikan Permissions

```
Setiap command yang didaftarkan WAJIB mendefinisikan permissions yang diperlukan.
Tidak boleh ada command tanpa permission check.

  ctx.plugin_manager.register_command(
      namespace=self.name,
      command="restart",
      handler=self.handlers.handle_restart,
      description="Restart kontainer Docker",
      permissions=["docker:write"]  # WAJIB, tidak boleh kosong untuk write ops
  )
```

### 11.4 Plugin Configuration via Database

```
Plugin TIDAK BOLEH menyimpan state atau konfigurasi di variabel class/instance
yang hilang saat bot restart.

State dan konfigurasi WAJIB disimpan di database (tabel plugin_configs atau custom).
```

---

## 12. Testing Rule

### 12.1 Coverage Minimum

```
Target coverage:
  - core/ : > 90%
  - plugins/ : > 80%
  - utils/ : > 90%
  - interfaces/ : > 95% (abstract class dan contract)

Cara ukur:
  uv run pytest --cov=guardian --cov-report=term-missing
```

### 12.2 Test Isolation

```
Setiap test harus independen:
  - Tidak bergantung pada urutan eksekusi test
  - Tidak berbagi state dengan test lain
  - Gunakan fixtures untuk setup dan teardown
  - Gunakan in-memory SQLite untuk test database
```

### 12.3 Mocking External Services

```
Test TIDAK BOLEH membuat koneksi ke:
  - Telegram API
  - Docker API
  - Internet (HTTP requests)
  - File system production

Gunakan pytest-mock untuk mock semua service eksternal.

  @pytest.fixture
  def mock_docker_client(mocker):
      return mocker.patch("guardian.plugins.docker.service.docker.from_env")
```

### 12.4 Test Naming yang Jelas

```
Nama test harus mendeskripsikan skenario dan expected result:

  BENAR:
    def test_authenticate_with_registered_user_returns_authorized()
    def test_authenticate_with_unregistered_user_returns_denied()
    def test_restart_container_when_docker_unavailable_raises_error()
    def test_rate_limit_blocks_user_after_30_commands_in_60_seconds()

  SALAH:
    def test_auth()
    def test_docker()
    def test_1()
```

### 12.5 Unit vs Integration Test

```
Unit Test (tests/unit/):
  - Test satu unit (class/function) secara terisolasi
  - Semua dependensi di-mock
  - Cepat (< 1 detik per test)
  - Harus run setiap kali sebelum commit

Integration Test (tests/integration/):
  - Test interaksi beberapa modul
  - Menggunakan in-memory database (bukan mock)
  - Boleh lebih lambat
  - Run di CI pipeline
```

---

## 13. Branching Strategy

### 13.1 Branch Model: GitHub Flow

```
main            <- Branch produksi. Selalu stabil dan deployable.
develop         <- Branch pengembangan aktif. Merge ke main untuk release.
feature/*       <- Fitur baru. Dibuat dari develop.
fix/*           <- Bug fix. Dibuat dari develop (atau main jika hotfix).
docs/*          <- Update dokumentasi saja.
release/*       <- Persiapan release. Dibuat dari develop.
hotfix/*        <- Fix kritis di production. Dibuat dari main.
```

### 13.2 Aturan Branch

```
main:
  - Dilindungi (protected branch)
  - Tidak boleh push langsung
  - Hanya merge via Pull Request
  - PR harus di-review minimal 1 orang
  - Semua CI checks harus lulus

feature/*:
  - Format: feature/nama-fitur-singkat
  - Contoh: feature/docker-plugin, feature/alert-system
  - Dibuat dari develop
  - Dihapus setelah merge

fix/*:
  - Format: fix/deskripsi-singkat
  - Contoh: fix/auth-race-condition

hotfix/*:
  - Dibuat dari main
  - Di-merge ke main DAN develop setelah selesai
```

---

## 14. Commit Convention

### 14.1 Format Commit Message

Menggunakan Conventional Commits specification:

```
Format:
  <type>(<scope>): <description>

  [optional body]

  [optional footer]

Type yang valid:
  feat:     Fitur baru
  fix:      Bug fix
  docs:     Perubahan dokumentasi saja
  style:    Perubahan formatting (tidak mengubah logika)
  refactor: Refaktor kode (bukan fix, bukan fitur baru)
  test:     Tambah atau perbaiki test
  chore:    Perubahan build system, dependency, CI
  perf:     Perbaikan performa
  security: Perbaikan keamanan

Scope (opsional, nama modul atau plugin):
  core, auth, docker, service, notification, scheduler, db, ci, deps
```

### 14.2 Contoh Commit Message

```
feat(docker): tambah command restart kontainer dengan konfirmasi

Implementasi restart kontainer Docker melalui Telegram dengan:
- Tampilkan detail kontainer sebelum restart
- Konfirmasi dua langkah untuk keamanan
- Kirim status baru setelah restart berhasil

Closes #42

---

fix(auth): perbaiki race condition saat autentikasi paralel

Dua request dari user yang sama dapat masuk bersamaan dan keduanya
lolos validasi sebelum sesi dibuat. Perbaikan menggunakan database
transaction untuk memastikan atomicity.

---

docs: perbarui 07_PLUGIN_SYSTEM.md dengan contoh alur lengkap

---

test(docker): tambah unit test untuk DockerService.restart_container

Coverage naik dari 76% ke 89% untuk modul docker/service.py
```

### 14.3 Aturan Commit

```
- Gunakan bahasa Inggris untuk commit message (untuk komunitas internasional)
- Gunakan imperative mood: "Add feature" bukan "Added feature"
- Baris pertama maksimal 72 karakter
- Pisahkan judul dan body dengan baris kosong
- Body jelaskan MENGAPA, bukan APA (kode sudah menjelaskan APA-nya)
- Referensi issue jika ada: "Closes #42", "Fixes #17"
```

---

## 15. Release Rule

### 15.1 Semantic Versioning

```
Format: MAJOR.MINOR.PATCH

MAJOR: Perubahan yang TIDAK backward-compatible
       - Perubahan API plugin yang breaking
       - Perubahan schema database yang memerlukan migrasi kompleks

MINOR: Fitur baru yang backward-compatible
       - Plugin baru
       - Command baru

PATCH: Bug fix backward-compatible
       - Fix bug
       - Perbaikan keamanan minor
       - Update dependency patch version
```

### 15.2 Proses Release

```
1. Buat branch release/vX.Y.Z dari develop
2. Update CHANGELOG.md dengan semua perubahan sejak release terakhir
3. Update versi di pyproject.toml
4. Update versi di guardian/__init__.py (jika ada)
5. Jalankan seluruh test suite
6. Merge release branch ke main via PR
7. Tag commit dengan vX.Y.Z
8. Push tag ke GitHub (trigger release workflow)
9. Merge main ke develop untuk sinkronisasi
```

### 15.3 CHANGELOG Format

```
# Changelog

## [Unreleased]

## [1.1.0] - 2026-10-01

### Added
- Plugin Nginx Manager: kelola virtual host dari Telegram
- Plugin Firewall (UFW): kelola firewall dari Telegram

### Fixed
- Race condition saat autentikasi paralel (#42)
- Memory leak di Docker stats polling (#38)

### Security
- Perbaiki validasi nama layanan yang rentan path traversal (#40)

### Changed
- Progress bar kini menggunakan karakter Unicode yang lebih jelas
```

---

## 16. Quality Checklist

Checklist ini WAJIB diverifikasi sebelum setiap PR di-merge ke main atau develop.

### Checklist Per File

- [ ] File tidak melebihi 500 baris
- [ ] Tidak ada circular import
- [ ] Semua fungsi memiliki type hint
- [ ] Tidak ada konfigurasi yang di-hardcode
- [ ] Tidak ada komentar yang tidak perlu
- [ ] Ruff check lulus: `uv run ruff check .`
- [ ] Mypy lulus: `uv run mypy .`

### Checklist Per Fitur

- [ ] Unit test ditulis untuk semua logika bisnis baru
- [ ] Integration test ditulis untuk alur utama
- [ ] Coverage tidak turun dari baseline
- [ ] Tidak ada breaking change tanpa dokumentasi dan versioning
- [ ] Dokumentasi di-update jika API berubah
- [ ] CHANGELOG.md di-update

### Checklist Per Plugin Baru

- [ ] Plugin mengikuti struktur standar (plugin.py, handlers.py, service.py)
- [ ] Plugin mendefinisikan semua metadata wajib
- [ ] Plugin tidak mengimport plugin lain secara langsung
- [ ] Semua command mendefinisikan permissions
- [ ] Plugin menangani kegagalan secara graceful (tidak crash bot)
- [ ] Plugin memiliki health_check yang berfungsi
- [ ] Plugin memiliki unit test dengan coverage > 80%
- [ ] Plugin terdokumentasi di README atau docs/

### Checklist Keamanan

- [ ] Tidak ada secret yang di-hardcode
- [ ] Input divalidasi sebelum digunakan
- [ ] subprocess tidak menggunakan shell=True
- [ ] Semua operasi berbahaya memerlukan konfirmasi
- [ ] Permission check ada di semua write operations
- [ ] Audit log mencatat tindakan baru

### Checklist Sebelum Release

- [ ] Semua test lulus di CI
- [ ] Coverage tidak di bawah target
- [ ] CHANGELOG.md sudah di-update
- [ ] Versi di pyproject.toml sudah di-update
- [ ] Tidak ada TODO/FIXME kritis yang belum diselesaikan
- [ ] Deployment script telah diuji di environment bersih
- [ ] Dokumen teknis yang relevan sudah di-update

---

## 17. Keputusan Desain

### Mengapa Conventional Commits?

Conventional Commits memungkinkan pembuatan CHANGELOG otomatis, menentukan versi bump otomatis, dan membuat riwayat commit yang mudah dibaca oleh mesin dan manusia. Ini adalah standar industri yang diterima luas.

### Mengapa 500 Baris Maksimum per File?

500 baris adalah batas praktis yang memaksa pengembang untuk memecah modul menjadi unit yang lebih kecil dan terfokus. File yang lebih besar dari ini hampir selalu dapat dipecah menjadi beberapa file dengan tanggung jawab yang lebih jelas.

### Mengapa No Comment Policy yang Ketat?

Komentar yang menjelaskan APA yang dilakukan kode adalah tanda bahwa kode tidak cukup jelas. Daripada menambah komentar, perbaiki nama variabel dan fungsinya. Komentar yang hanya menjelaskan APA menjadi stale dan menyesatkan saat kode berubah tapi komentar tidak.

### Mengapa Strict Mypy?

Strict mypy memaksa pengembang untuk menulis type hint yang lengkap dan benar. Ini menemukan banyak bug potensial sebelum runtime dan membuat kode lebih mudah dipahami oleh IDE dan pengembang lain.

---

*Dokumen ini adalah aturan tertinggi pengembangan Serverinka Guardian.*
*Referensi: Seluruh dokumen teknis 01_PRD.md hingga 09_DEPLOYMENT.md*
