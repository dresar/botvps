"""Plugin ai_assistant — integrasi AI Chat Assistant berbasis Gemini 2.5 Flash."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class AIAssistantPlugin(BasePlugin):
    """Plugin AI Chat Assistant untuk menjawab pertanyaan seputar sistem & VPS."""

    @property
    def name(self) -> str:
        return "ai_assistant"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "AI Chat Assistant (Gemini 2.5 Flash API Gateway)"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command AI."""
        from guardian.plugins.ai_assistant.handlers import AIAssistantHandlers
        h = AIAssistantHandlers()

        ctx.plugin_manager.register_command(
            namespace="ask",
            command="menu",
            handler=h.handle_ask,
            permissions=["system:read"],
            description="Tanya AI Assistant Gemini",
        )
        ctx.plugin_manager.register_command(
            namespace="ai",
            command="ask",
            handler=h.handle_ask,
            permissions=["system:read"],
            description="Tanya AI Assistant Gemini",
        )

        logger.info("AIAssistantPlugin siap.")

    async def health_check(self) -> PluginHealth:
        """Cek kesehatan AI plugin."""
        return PluginHealth(
            plugin_name=self.name,
            status="healthy",
            message="AI Assistant Plugin aktif.",
            checked_at=datetime.utcnow(),
        )
