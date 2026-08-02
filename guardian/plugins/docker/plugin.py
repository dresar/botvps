"""Plugin docker — manajemen Docker kontainer."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class DockerPlugin(BasePlugin):
    """Plugin untuk mengelola Docker kontainer melalui Telegram."""

    @property
    def name(self) -> str:
        return "docker"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Manajemen Docker kontainer (list, start, stop, restart, log, images)"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command dan callback."""
        if not ctx.settings.docker_enabled:
            logger.info("DockerPlugin dinonaktifkan via konfigurasi.")
            return

        from guardian.plugins.docker.handlers import DockerHandlers
        h = DockerHandlers()

        ctx.plugin_manager.register_command(
            namespace="docker",
            command="list",
            handler=h.handle_list,
            permissions=["docker:read"],
            description="Daftar kontainer Docker",
        )
        ctx.plugin_manager.register_command(
            namespace="docker",
            command="status",
            handler=h.handle_status,
            permissions=["docker:read"],
            description="Status detail kontainer",
        )
        ctx.plugin_manager.register_command(
            namespace="docker",
            command="start",
            handler=h.handle_control,
            permissions=["docker:write"],
            description="Start kontainer",
        )
        ctx.plugin_manager.register_command(
            namespace="docker",
            command="stop",
            handler=h.handle_control,
            permissions=["docker:write"],
            description="Stop kontainer",
        )
        ctx.plugin_manager.register_command(
            namespace="docker",
            command="restart",
            handler=h.handle_control,
            permissions=["docker:write"],
            description="Restart kontainer",
        )
        ctx.plugin_manager.register_command(
            namespace="docker",
            command="log",
            handler=h.handle_log,
            permissions=["docker:read"],
            description="Log kontainer",
        )
        ctx.plugin_manager.register_command(
            namespace="docker",
            command="images",
            handler=h.handle_images,
            permissions=["docker:read"],
            description="Daftar Docker images",
        )

        ctx.plugin_manager.register_callback("docker", h.handle_callback)
        logger.info("DockerPlugin siap.")

    async def health_check(self) -> PluginHealth:
        """Cek koneksi Docker daemon."""
        try:
            from guardian.plugins.docker.service import DockerService
            status = "healthy"
            message = "Docker tersedia."
        except Exception as e:
            status = "degraded"
            message = f"Docker tidak tersedia: {e}"

        return PluginHealth(
            plugin_name=self.name,
            status=status,
            message=message,
            checked_at=datetime.utcnow(),
        )
