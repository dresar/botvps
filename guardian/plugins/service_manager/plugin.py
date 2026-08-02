"""Plugin service_manager — manajemen layanan systemd."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class ServiceManagerPlugin(BasePlugin):
    """Plugin untuk mengelola layanan systemd melalui Telegram."""

    @property
    def name(self) -> str:
        return "service_manager"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Manajemen layanan systemd (start, stop, restart, log)"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command dan callback handler."""
        from guardian.plugins.service_manager.handlers import ServiceManagerHandlers
        h = ServiceManagerHandlers()

        ctx.plugin_manager.register_command(
            namespace="service",
            command="list",
            handler=h.handle_list,
            permissions=["service:read"],
            description="Daftar layanan systemd",
        )
        ctx.plugin_manager.register_command(
            namespace="service",
            command="status",
            handler=h.handle_status,
            permissions=["service:read"],
            description="Status detail layanan",
        )
        ctx.plugin_manager.register_command(
            namespace="service",
            command="start",
            handler=h.handle_control,
            permissions=["service:write"],
            description="Start layanan",
        )
        ctx.plugin_manager.register_command(
            namespace="service",
            command="stop",
            handler=h.handle_control,
            permissions=["service:write"],
            description="Stop layanan",
        )
        ctx.plugin_manager.register_command(
            namespace="service",
            command="restart",
            handler=h.handle_control,
            permissions=["service:write"],
            description="Restart layanan",
        )
        ctx.plugin_manager.register_command(
            namespace="service",
            command="log",
            handler=h.handle_log,
            permissions=["service:read"],
            description="Lihat log layanan",
        )

        ctx.plugin_manager.register_callback("service", h.handle_callback)

        logger.info("ServiceManagerPlugin siap.")

    async def health_check(self) -> PluginHealth:
        """Cek apakah systemctl tersedia."""
        from guardian.utils.sandbox import run_command
        result = await run_command(["systemctl", "--version"])
        status = "healthy" if result.success else "degraded"
        return PluginHealth(
            plugin_name=self.name,
            status=status,
            message="systemctl tersedia." if result.success else "systemctl tidak tersedia.",
            checked_at=datetime.utcnow(),
        )
