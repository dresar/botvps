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
        from guardian.plugins.scheduler_ui.handlers import SchedulerUIHandlers
        from guardian.plugins.scheduler_ui.service import AISchedulerService

        self._ai_sched_service = AISchedulerService(ctx)
        await self._ai_sched_service.register_tasks_to_engine()

        h = SchedulerUIHandlers(self._ai_sched_service)

        for ns in ("schedule", "remind", "reminder"):
            for cmd in ("list", "show", "menu", "add", "del", "delete", "pause", "resume"):
                try:
                    ctx.plugin_manager.register_command(
                        namespace=ns,
                        command=cmd,
                        handler=h.handle_schedule_router,
                        permissions=["schedule:read"],
                        description="Manajemen scheduled jobs & reminders",
                    )
                except Exception:
                    pass

        logger.info("SchedulerUIPlugin siap.")

    async def health_check(self) -> PluginHealth:
        return PluginHealth(
            plugin_name=self.name,
            status="healthy",
            message="SchedulerUI berjalan normal.",
            checked_at=datetime.utcnow(),
        )
