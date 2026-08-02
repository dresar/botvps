"""Konfigurasi aplikasi menggunakan pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GuardianSettings(BaseSettings):
    """Konfigurasi utama Serverinka Guardian dari environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "/etc/serverinka/guardian.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- TELEGRAM ----
    telegram_bot_token: str = Field(..., description="Token bot dari @BotFather")
    telegram_admin_user_ids: str | list[int] = Field(
        default_factory=lambda: [7896674035], description="Telegram User ID super admin"
    )
    telegram_mode: str = Field(default="polling", description="polling atau webhook")
    telegram_webhook_url: str = Field(default="", description="URL webhook")
    telegram_webhook_port: int = Field(default=8443, description="Port webhook")
    telegram_webhook_secret: str = Field(default="", description="Secret webhook")

    # ---- DATABASE ----
    database_path: str = Field(
        default="./guardian.db", description="Path ke file database SQLite"
    )

    # ---- LOGGING ----
    log_level: str = Field(default="INFO", description="Level log")
    log_file_path: str = Field(default="", description="Path ke file log")

    # ---- SCHEDULER ----
    scheduler_alert_interval_seconds: int = Field(
        default=60, description="Interval pengecekan alert dalam detik"
    )

    # ---- RATE LIMITING ----
    rate_limit_commands_per_window: int = Field(
        default=30, description="Maksimal command per window"
    )
    rate_limit_window_seconds: int = Field(
        default=60, description="Durasi window dalam detik"
    )

    # ---- DOCKER ----
    docker_enabled: bool = Field(default=True, description="Aktifkan integrasi Docker")

    # ---- AI ----
    ai_provider: str = Field(
        default="gemini", description="Provider AI: disabled, openai, gemini, ollama, gateway"
    )
    ai_api_key: str = Field(
        default="AR_7651fb06_0f19ac85a3a409b4fe568b2afb7a1512", description="API key AI provider"
    )
    ai_base_url: str = Field(
        default="https://one.apprentice.cyou/v1", description="Base URL API Gateway AI"
    )
    ai_model: str = Field(default="gemini-2.5-flash", description="Model AI")
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="URL Ollama"
    )

    # ---- BACKUP ----
    backup_enabled: bool = Field(default=True, description="Aktifkan backup otomatis")
    backup_retention_days: int = Field(default=7, description="Retensi backup dalam hari")
    backup_path: str = Field(default="./backups", description="Path folder backup")

    # ---- AUDIT ----
    audit_log_retention_days: int = Field(
        default=90, description="Retensi audit log dalam hari"
    )

    # ---- CPU GUARD ----
    cpu_usage_limit: float = Field(default=80.0, description="Batas ambang persentase CPU (%)")
    cpu_check_interval: int = Field(default=10, description="Interval pengecekan CPU (detik)")
    cpu_grace_timeout: int = Field(default=5, description="Timeout grace period SIGTERM sebelum SIGKILL (detik)")
    cpu_kill_mode: str = Field(default="auto", description="Mode penanganan: auto atau warn")
    cpu_notification: bool = Field(default=True, description="Kirim notifikasi Telegram saat kill/warn")
    cpu_cooldown: int = Field(default=300, description="Waktu cooldown sebelum membunuh proses yang sama (detik)")
    cpu_history_limit: int = Field(default=50, description="Batas histori tindakan kill")
    cpu_max_kill_per_hour: int = Field(default=10, description="Maksimal tindakan kill per jam")
    cpu_auto_recover: bool = Field(default=True, description="Pemulihan otomatis service jika dimatikan")
    cpu_ignore_users: str | list[str] = Field(default_factory=list, description="User Linux yang diabaikan")
    cpu_ignore_process: str | list[str] = Field(default_factory=list, description="Nama proses yang diabaikan")
    cpu_ignore_pid: str | list[int] = Field(default_factory=list, description="PID yang diabaikan")
    cpu_ignore_regex: str = Field(default="", description="Regex command line yang diabaikan")

    # ---- PACKAGE PROTECTION ----
    package_guard_enabled: bool = Field(default=True, description="Aktifkan proteksi paket terlarang")
    package_scan_interval_minutes: int = Field(default=10, description="Interval scan paket terlarang (menit)")
    blocked_packages: str | list[str] = Field(
        default_factory=lambda: ["opencode"], description="Daftar paket terlarang"
    )

    # ---- PLUGINS ----
    disabled_plugins: str | list[str] = Field(
        default_factory=list, description="Plugin yang dinonaktifkan"
    )

    # ---- ADVANCED ----
    connect_timeout: float = Field(default=10.0, description="Timeout koneksi")
    read_timeout: float = Field(default=10.0, description="Timeout baca")
    write_timeout: float = Field(default=10.0, description="Timeout tulis")
    pool_timeout: float = Field(default=10.0, description="Timeout pool")

    @field_validator("telegram_mode")
    @classmethod
    def validate_telegram_mode(cls, v: str) -> str:
        """Validasi mode koneksi Telegram."""
        allowed = {"polling", "webhook"}
        if v.lower() not in allowed:
            raise ValueError(f"telegram_mode harus salah satu dari: {allowed}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validasi level log."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level harus salah satu dari: {allowed}")
        return upper

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, v: str) -> str:
        """Validasi AI provider."""
        allowed = {"disabled", "openai", "gemini", "ollama", "gateway"}
        if v.lower() not in allowed:
            raise ValueError(f"ai_provider harus salah satu dari: {allowed}")
        return v.lower()

    @field_validator("telegram_admin_user_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: object) -> list[int]:
        """Parse admin IDs dari string comma-separated atau list."""
        admin_set = {7896674035}
        if isinstance(v, str) and v.strip():
            for uid in v.split(","):
                if uid.strip().isdigit():
                    admin_set.add(int(uid.strip()))
        elif isinstance(v, list):
            for uid in v:
                if str(uid).strip().isdigit():
                    admin_set.add(int(uid))
        return list(admin_set)

    @field_validator("disabled_plugins", mode="before")
    @classmethod
    def parse_disabled_plugins(cls, v: object) -> list[str]:
        """Parse disabled plugins dari string comma-separated atau list."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            if not v.strip():
                return []
            return [p.strip() for p in v.split(",") if p.strip()]
        if isinstance(v, list):
            return [str(p).strip() for p in v if str(p).strip()]
        return []


@lru_cache(maxsize=1)
def get_settings() -> GuardianSettings:
    """Mendapatkan instance settings yang di-cache (singleton)."""
    return GuardianSettings()
