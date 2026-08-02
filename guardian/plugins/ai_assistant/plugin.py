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

    def __init__(self) -> None:
        self._service: AIAssistantService | None = None

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
        from guardian.plugins.ai_assistant.service import AIAssistantService

        self._service = AIAssistantService(ctx)
        h = AIAssistantHandlers(self._service)

        for ns in ("ask", "ai"):
            for cmd in ("menu", "ask", "help", "addkey", "addkeys", "keys", "keylist", "delkey", "clearkeys"):
                try:
                    ctx.plugin_manager.register_command(
                        namespace=ns,
                        command=cmd,
                        handler=h.handle_ask,
                        permissions=["system:read"],
                        description="Tanya AI Assistant Gemini & Key Pool",
                    )
                except Exception:
                    pass

        logger.info("AIAssistantPlugin siap.")

    async def health_check(self) -> PluginHealth:
        """Cek kesehatan AI plugin."""
        is_healthy = self._service is not None and self._service.ai_client.is_enabled
        return PluginHealth(
            plugin_name=self.name,
            status="healthy" if is_healthy else "degraded",
            message="AI Assistant Siap." if is_healthy else "AI Assistant Disabled.",
            checked_at=datetime.utcnow(),
        )
