"""Plugin user_manager — manajemen pengguna Serverinka Guardian."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class UserManagerPlugin(BasePlugin):
    """Plugin untuk mengelola pengguna bot melalui Telegram."""

    @property
    def name(self) -> str:
        return "user_manager"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Manajemen pengguna bot (tambah, ubah role, nonaktifkan)"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan command handler user_manager."""
        from guardian.plugins.user_manager.handlers import UserManagerHandlers
        h = UserManagerHandlers()

        ctx.plugin_manager.register_command(
            namespace="user",
            command="list",
            handler=h.handle_list,
            permissions=["user:read"],
            description="Daftar pengguna terdaftar",
        )
        ctx.plugin_manager.register_command(
            namespace="user",
            command="add",
            handler=h.handle_add,
            permissions=["user:write"],
            description="Tambah pengguna baru",
        )
        ctx.plugin_manager.register_command(
            namespace="user",
            command="role",
            handler=h.handle_role,
            permissions=["user:write"],
            description="Ubah role pengguna",
        )
        ctx.plugin_manager.register_command(
            namespace="user",
            command="remove",
            handler=h.handle_remove,
            permissions=["user:write"],
            description="Nonaktifkan pengguna",
        )

        logger.info("UserManagerPlugin siap.")

    async def health_check(self) -> PluginHealth:
        return PluginHealth(
            plugin_name=self.name,
            status="healthy",
            message="User Manager berjalan normal.",
            checked_at=datetime.utcnow(),
        )
