"""Plugin system — monitoring server."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class SystemPlugin(BasePlugin):
    """Plugin monitoring sistem: CPU, RAM, Disk, Jaringan, Proses."""

    @property
    def name(self) -> str:
        return "system"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Monitoring resource server (CPU, RAM, Disk, Network)"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command dan callback handler."""
        from guardian.plugins.system.handlers import SystemHandlers
        h = SystemHandlers()

        ctx.plugin_manager.register_command(
            namespace="system",
            command="status",
            handler=h.handle_status,
            permissions=["system:read"],
            description="Dashboard status server",
        )
        ctx.plugin_manager.register_command(
            namespace="system",
            command="cpu",
            handler=h.handle_cpu,
            permissions=["system:read"],
            description="Detail penggunaan CPU",
        )
        ctx.plugin_manager.register_command(
            namespace="system",
            command="ram",
            handler=h.handle_ram,
            permissions=["system:read"],
            description="Detail penggunaan RAM",
        )
        ctx.plugin_manager.register_command(
            namespace="system",
            command="disk",
            handler=h.handle_disk,
            permissions=["system:read"],
            description="Detail penggunaan disk",
        )
        ctx.plugin_manager.register_command(
            namespace="system",
            command="net",
            handler=h.handle_net,
            permissions=["system:read"],
            description="Statistik jaringan",
        )
        ctx.plugin_manager.register_command(
            namespace="system",
            command="proc",
            handler=h.handle_proc,
            permissions=["system:read"],
            description="Top proses berdasarkan CPU",
        )

        ctx.plugin_manager.register_callback("system", h.handle_reboot_callback)

        logger.info("SystemPlugin siap.")

    async def health_check(self) -> PluginHealth:
        """Cek kesehatan plugin system."""
        try:
            import psutil
            psutil.cpu_percent(interval=None)
            return PluginHealth(
                plugin_name=self.name,
                status="healthy",
                message="psutil tersedia dan berjalan normal.",
                checked_at=datetime.utcnow(),
            )
        except ImportError:
            return PluginHealth(
                plugin_name=self.name,
                status="unhealthy",
                message="psutil tidak terinstall.",
                checked_at=datetime.utcnow(),
            )
