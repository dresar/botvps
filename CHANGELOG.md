# Changelog

Semua perubahan signifikan pada proyek **Serverinka Guardian** akan didokumentasikan di file ini.

Format changelog berbasis pada [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), dan proyek ini mematuhi [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-08-02

### Added
- **Arsitektur Core:**
  - `GuardianEngine` dengan ApplicationContext dependency injection.
  - Integration dengan `python-telegram-bot` v21.
  - `EventBus` pub/sub async dengan error isolation per subscriber.
  - `DatabaseManager` berbasis `aiosqlite` dengan auto-migration runner.
  - `AuthService` RBAC berbasis Telegram ID dengan 4 tingkatan role (`super_admin`, `admin`, `operator`, `viewer`).
  - `SchedulerEngine` berbasis `APScheduler` (cron & interval trigger).
  - Subprocess Sandbox terisolasi tanpa `shell=True` dengan timeout enforcement.

- **Sistem Plugin & Auto-Discovery:**
  - Framework `BasePlugin`, `BaseService`, dan `BaseRepository`.
  - Topological sorting untuk urutan pemuatan dependensi antar plugin.

- **Plugins Inisial (7 Plugin Core):**
  - `system`: Monitoring CPU, RAM, Disk, Network, & Top Processes via `psutil`.
  - `service_manager`: Kontrol & monitoring `systemd` service (`systemctl` & `journalctl`).
  - `docker`: Kontrol & stats Docker container dan images (`docker` SDK).
  - `notification`: Background threshold checker & multi-admin broadcast notification.
  - `user_manager`: Management whitelist user Telegram, penetapan role, dan blokir.
  - `scheduler_ui`: Visualisasi & pengontrolan scheduled background jobs.
  - `audit_viewer`: Log inspeksi real-time untuk seluruh aksi pengguna.

- **Tooling & Deployment:**
  - Automated deployment setup script `scripts/setup.sh` untuk Debian 12 & Ubuntu Server.
  - Script update `scripts/update.sh` dan script backup SQLite `scripts/backup.sh`.
  - Aturan Sudoers minimal privilose `scripts/sudoers.d/serverinka`.
  - GitHub Actions CI workflow untuk linting (`ruff`), typing (`mypy`), dan testing (`pytest`).
