"""Terminal Plugin — Full Shell Access via Telegram."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class TerminalPlugin(BasePlugin):
    """Plugin terminal: eksekusi perintah shell Linux langsung dari Telegram."""

    @property
    def name(self) -> str:
        return "terminal"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Full SSH-like shell access — eksekusi perintah Linux via Telegram"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command dan callback handler terminal."""
        from guardian.plugins.terminal.handlers import TerminalHandlers

        h = TerminalHandlers()

        # Perintah utama: /run <command>
        ctx.plugin_manager.register_command(
            namespace="terminal",
            command="run",
            handler=h.handle_run,
            permissions=["terminal:execute"],
            description="Eksekusi perintah shell Linux",
        )
        # /history
        ctx.plugin_manager.register_command(
            namespace="terminal",
            command="history",
            handler=h.handle_history,
            permissions=["terminal:read"],
            description="Riwayat perintah terminal",
        )
        # /terminal (info menu)
        ctx.plugin_manager.register_command(
            namespace="terminal",
            command="menu",
            handler=h.handle_terminal_menu,
            permissions=["terminal:read"],
            description="Menu & info terminal",
        )
        # /terminal reset
        ctx.plugin_manager.register_command(
            namespace="terminal",
            command="reset",
            handler=h.handle_session_reset,
            permissions=["terminal:execute"],
            description="Reset sesi terminal",
        )
        # Callback buttons
        ctx.plugin_manager.register_callback("terminal", h.handle_callback)

        logger.info("TerminalPlugin siap.")

    async def health_check(self) -> PluginHealth:
        """Cek kesehatan plugin terminal."""
        try:
            import shutil
            bash_path = shutil.which("bash") or shutil.which("sh")
            return PluginHealth(
                plugin_name=self.name,
                status="healthy",
                message=f"Shell tersedia di: {bash_path}",
                checked_at=datetime.utcnow(),
            )
        except Exception as e:
            return PluginHealth(
                plugin_name=self.name,
                status="unhealthy",
                message=f"Shell tidak tersedia: {e}",
                checked_at=datetime.utcnow(),
            )
