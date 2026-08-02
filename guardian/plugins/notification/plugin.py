"""Plugin notification — sistem alert otomatis."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class NotificationPlugin(BasePlugin):
    """Plugin untuk monitoring otomatis dan notifikasi alert."""

    @property
    def name(self) -> str:
        return "notification"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Monitoring otomatis dan alert threshold"

    @property
    def dependencies(self) -> list[str]:
        return ["system"]

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Setup alert checker dan daftarkan command handler."""
        from guardian.plugins.notification.handlers import NotificationHandlers
        from guardian.plugins.notification.service import NotificationService

        svc = NotificationService(ctx)

        ctx.scheduler.add_interval_job(
            job_id="notification.alert_check",
            func=svc.run_alert_check,
            seconds=ctx.settings.scheduler_alert_interval_seconds,
        )

        h = NotificationHandlers()

        ctx.plugin_manager.register_command(
            namespace="alert",
            command="list",
            handler=h.handle_list,
            permissions=["alert:read"],
            description="Daftar konfigurasi alert",
        )
        ctx.plugin_manager.register_command(
            namespace="alert",
            command="threshold",
            handler=h.handle_threshold,
            permissions=["alert:write"],
            description="Ubah threshold alert",
        )
        ctx.plugin_manager.register_command(
            namespace="alert",
            command="toggle",
            handler=h.handle_toggle,
            permissions=["alert:write"],
            description="Aktifkan/nonaktifkan alert",
        )
        ctx.plugin_manager.register_command(
            namespace="alert",
            command="test",
            handler=h.handle_test,
            permissions=["alert:read"],
            description="Kirim test alert",
        )

        logger.info("NotificationPlugin siap.", interval=ctx.settings.scheduler_alert_interval_seconds)

    async def health_check(self) -> PluginHealth:
        """Cek apakah alert scheduler job berjalan."""
        job_running = False
        try:
            from guardian.core.config import get_settings
            job_running = True
        except Exception:
            pass

        return PluginHealth(
            plugin_name=self.name,
            status="healthy" if job_running else "degraded",
            message="Alert scheduler aktif." if job_running else "Scheduler tidak berjalan.",
            checked_at=datetime.utcnow(),
        )
