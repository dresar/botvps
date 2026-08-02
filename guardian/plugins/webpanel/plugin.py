"""Plugin WebPanel — handler /panel command untuk membuka Telegram Mini App."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class WebPanelPlugin(BasePlugin):
    """Plugin WebPanel: membuka Telegram Mini App dari bot."""

    @property
    def name(self) -> str:
        return "webpanel"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Telegram Mini App — Web Panel kontrol VPS"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command /panel."""
        from guardian.plugins.webpanel.handlers import WebPanelHandlers
        h = WebPanelHandlers()

        ctx.plugin_manager.register_command(
            namespace="webpanel",
            command="open",
            handler=h.handle_open_panel,
            permissions=["webpanel:access"],
            description="Buka Web Panel VPS",
        )
        logger.info("WebPanelPlugin siap.")

    async def health_check(self) -> PluginHealth:
        return PluginHealth(
            plugin_name=self.name,
            status="healthy",
            message="WebPanel plugin aktif.",
            checked_at=datetime.utcnow(),
        )
