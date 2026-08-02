"""Plugin audit_viewer — tampilan audit log sistem."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class AuditViewerPlugin(BasePlugin):
    """Plugin untuk melihat audit log tindakan pengguna."""

    @property
    def name(self) -> str:
        return "audit_viewer"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Tampilan audit log semua tindakan pengguna"

    @property
    def dependencies(self) -> list[str]:
        return ["user_manager"]

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command audit."""
        from guardian.plugins.audit_viewer.handlers import AuditViewerHandlers
        h = AuditViewerHandlers()

        ctx.plugin_manager.register_command(
            namespace="audit",
            command="list",
            handler=h.handle_list,
            permissions=["audit:read"],
            description="Audit log terbaru",
        )
        ctx.plugin_manager.register_command(
            namespace="audit",
            command="user",
            handler=h.handle_user,
            permissions=["audit:read"],
            description="Audit log per user",
        )

        logger.info("AuditViewerPlugin siap.")

    async def health_check(self) -> PluginHealth:
        return PluginHealth(
            plugin_name=self.name,
            status="healthy",
            message="Audit Viewer berjalan normal.",
            checked_at=datetime.utcnow(),
        )
