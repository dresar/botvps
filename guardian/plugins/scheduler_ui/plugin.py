"""Plugin scheduler_ui — antarmuka manajemen scheduled jobs."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class SchedulerUIPlugin(BasePlugin):
    """Plugin untuk mengelola scheduled jobs melalui Telegram."""

    @property
    def name(self) -> str:
        return "scheduler_ui"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Manajemen scheduled jobs (list, pause, resume)"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command scheduler."""
        from guardian.plugins.scheduler_ui.handlers import SchedulerUIHandlers
        h = SchedulerUIHandlers()

        ctx.plugin_manager.register_command(
            namespace="schedule",
            command="list",
            handler=h.handle_list,
            permissions=["schedule:read"],
            description="Daftar scheduled jobs",
        )
        ctx.plugin_manager.register_command(
            namespace="schedule",
            command="pause",
            handler=h.handle_pause,
            permissions=["schedule:write"],
            description="Pause scheduled job",
        )
        ctx.plugin_manager.register_command(
            namespace="schedule",
            command="resume",
            handler=h.handle_resume,
            permissions=["schedule:write"],
            description="Resume scheduled job",
        )

        logger.info("SchedulerUIPlugin siap.")

    async def health_check(self) -> PluginHealth:
        return PluginHealth(
            plugin_name=self.name,
            status="healthy",
            message="SchedulerUI berjalan normal.",
            checked_at=datetime.utcnow(),
        )
