"""Konstanta nama event untuk EventBus Serverinka Guardian."""


class SystemEvents:
    """Event-event yang dihasilkan oleh core system."""

    STARTUP_COMPLETE = "system.startup_complete"
    SHUTDOWN_REQUESTED = "system.shutdown_requested"
    PLUGIN_LOADED = "system.plugin_loaded"
    PLUGIN_ERROR = "system.plugin_error"


class AuthEvents:
    """Event-event yang dihasilkan oleh AuthService."""

    USER_AUTHENTICATED = "auth.user_authenticated"
    USER_DENIED = "auth.user_denied"
    USER_BLOCKED = "auth.user_blocked"
    USER_ADDED = "auth.user_added"
    USER_ROLE_CHANGED = "auth.user_role_changed"


class AlertEvents:
    """Event-event yang dihasilkan oleh NotificationPlugin."""

    THRESHOLD_EXCEEDED = "alert.threshold_exceeded"
    SERVICE_DOWN = "alert.service_down"
    ALERT_SENT = "alert.sent"


class DockerEvents:
    """Event-event yang dihasilkan oleh DockerPlugin."""

    CONTAINER_STARTED = "docker.container_started"
    CONTAINER_STOPPED = "docker.container_stopped"
    CONTAINER_RESTARTED = "docker.container_restarted"


class ServiceEvents:
    """Event-event yang dihasilkan oleh ServiceManagerPlugin."""

    STARTED = "service.started"
    STOPPED = "service.stopped"
    RESTARTED = "service.restarted"
    FAILED = "service.failed"


class BackupEvents:
    """Event-event yang dihasilkan oleh backup system."""

    BACKUP_STARTED = "backup.started"
    BACKUP_COMPLETED = "backup.completed"
    BACKUP_FAILED = "backup.failed"
