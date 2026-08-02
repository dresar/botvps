"""Plugin ProcessGuardianPlugin — Auto Process CPU Guardian."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth
from guardian.plugins.process_guardian.handlers import CPUGuardHandlers
from guardian.plugins.process_guardian.service import ProcessGuardianService

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class ProcessGuardianPlugin(BasePlugin):
    """Plugin pengawas penggunaan CPU proses dan pencegah overload VPS."""

    def __init__(self) -> None:
        self._service: ProcessGuardianService | None = None

    @property
    def name(self) -> str:
        return "process_guardian"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Auto Process CPU Guardian & Overload Protection"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan service, handler, dan background scheduler job."""
        self._service = ProcessGuardianService(ctx)
        handlers = CPUGuardHandlers(self._service)

        ctx.plugin_manager.register_command(
            namespace="cpu_guard",
            command="menu",
            handler=handlers.handle_cpu_guard,
            permissions=["system:read"],
            description="Pengawas & Pelindung CPU VPS",
        )

        # Daftarkan background job scheduler internal untuk monitoring CPU
        interval = ctx.settings.cpu_check_interval
        ctx.scheduler.add_interval_job(
            job_id="process_guardian.cpu_check",
            func=self._service.check_and_enforce_cpu_limits,
            seconds=interval,
        )

        logger.info("ProcessGuardianPlugin siap.", interval=interval)

    async def health_check(self) -> PluginHealth:
        """Cek kesehatan plugin."""
        status = "healthy" if self._service and self._service.is_enabled else "degraded"
        return PluginHealth(
            plugin_name=self.name,
            status=status,
            message="CPU Guard Monitoring Aktif." if status == "healthy" else "CPU Guard Nonaktif.",
            checked_at=datetime.utcnow(),
        )
