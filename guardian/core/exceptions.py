"""Hierarki exception untuk Serverinka Guardian."""


class GuardianBaseError(Exception):
    """Exception dasar untuk semua error Serverinka Guardian."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __repr__(self) -> str:
        return f"{type(self).__name__}(message={self.message!r})"


# ---- Auth Errors ----


class AuthError(GuardianBaseError):
    """Error terkait autentikasi dan otorisasi."""


class UserNotFoundError(AuthError):
    """User tidak ditemukan di database."""


class UserAlreadyExistsError(AuthError):
    """User sudah terdaftar di sistem."""


class InvalidRoleError(AuthError):
    """Role yang diberikan tidak valid."""


class PermissionDeniedError(AuthError):
    """User tidak memiliki izin untuk tindakan ini."""


class UserBlockedError(AuthError):
    """User diblokir dari sistem."""


class UserInactiveError(AuthError):
    """Akun user tidak aktif."""


# ---- Plugin Errors ----


class PluginError(GuardianBaseError):
    """Error terkait sistem plugin."""


class PluginNotFoundError(PluginError):
    """Plugin yang diminta tidak ditemukan."""


class PluginLoadError(PluginError):
    """Gagal memuat plugin."""


class PluginSetupError(PluginError):
    """Gagal setup plugin (inisialisasi)."""


class PluginDependencyError(PluginError):
    """Dependensi plugin tidak terpenuhi."""


class PluginAlreadyRegisteredError(PluginError):
    """Plugin sudah terdaftar dengan nama yang sama."""


# ---- Service Errors ----


class ServiceError(GuardianBaseError):
    """Error terkait operasi layanan sistem."""


class ServiceNotFoundError(ServiceError):
    """Layanan systemd tidak ditemukan."""


class ServiceOperationError(ServiceError):
    """Operasi systemctl gagal."""


class ProcessNotFoundError(ServiceError):
    """Proses dengan PID yang diberikan tidak ditemukan."""


class CommandExecutionError(ServiceError):
    """Eksekusi subprocess gagal."""

    def __init__(self, message: str, return_code: int = -1, detail: str = "") -> None:
        super().__init__(message, detail)
        self.return_code = return_code


# ---- Docker Errors ----


class DockerError(GuardianBaseError):
    """Error terkait Docker."""


class DockerNotAvailableError(DockerError):
    """Docker daemon tidak dapat diakses."""


class ContainerNotFoundError(DockerError):
    """Kontainer Docker tidak ditemukan."""


class DockerOperationError(DockerError):
    """Operasi Docker gagal."""


class ImageNotFoundError(DockerError):
    """Docker image tidak ditemukan."""


# ---- Database Errors ----


class DatabaseError(GuardianBaseError):
    """Error terkait database."""


class MigrationError(DatabaseError):
    """Gagal menjalankan migrasi database."""


class QueryError(DatabaseError):
    """Gagal menjalankan query database."""


# ---- Config Errors ----


class ConfigError(GuardianBaseError):
    """Error terkait konfigurasi."""


class MissingConfigError(ConfigError):
    """Konfigurasi wajib tidak ditemukan."""


class InvalidConfigError(ConfigError):
    """Nilai konfigurasi tidak valid."""


# ---- AI Errors ----


class AIError(GuardianBaseError):
    """Error terkait AI gateway."""


class AIProviderNotConfiguredError(AIError):
    """AI provider tidak dikonfigurasi."""


class AIProviderError(AIError):
    """API call ke AI provider gagal."""


# ---- Scheduler Errors ----


class SchedulerError(GuardianBaseError):
    """Error terkait scheduler."""


class JobNotFoundError(SchedulerError):
    """Job terjadwal tidak ditemukan."""


class InvalidCronExpressionError(SchedulerError):
    """Ekspresi cron tidak valid."""


# ---- Rate Limit Error ----


class RateLimitError(GuardianBaseError):
    """User telah melewati batas rate limit."""

    def __init__(self, message: str, retry_after_seconds: int = 60) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
