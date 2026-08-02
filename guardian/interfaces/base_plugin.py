"""Abstract class BasePlugin — semua plugin harus mewarisi class ini."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext


@dataclass
class PluginHealth:
    """Status kesehatan plugin."""

    plugin_name: str
    status: str  # "healthy" | "degraded" | "unhealthy"
    message: str
    checked_at: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """Abstract class dasar untuk semua plugin Serverinka Guardian.

    Setiap plugin harus:
    1. Mewarisi BasePlugin.
    2. Mendefinisikan semua abstract properties.
    3. Mengimplementasikan setup() untuk mendaftarkan handler.
    4. Mengimplementasikan health_check() untuk monitoring.

    Contoh:
        class MyPlugin(BasePlugin):
            @property
            def name(self) -> str:
                return "my_plugin"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def description(self) -> str:
                return "Plugin contoh"

            @property
            def dependencies(self) -> list[str]:
                return []

            async def setup(self, ctx: "ApplicationContext") -> None:
                ctx.plugin_manager.register_command(
                    namespace=self.name,
                    command="hello",
                    handler=self._handle_hello,
                    permissions=[],
                    description="Ucapkan halo",
                )

            async def health_check(self) -> PluginHealth:
                return PluginHealth(
                    plugin_name=self.name,
                    status="healthy",
                    message="Plugin berjalan normal.",
                )
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier unik plugin. Gunakan snake_case."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Versi semantic plugin. Format: MAJOR.MINOR.PATCH."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Deskripsi singkat plugin."""

    @property
    @abstractmethod
    def dependencies(self) -> list[str]:
        """Nama plugin lain yang harus dimuat sebelum plugin ini."""

    @abstractmethod
    async def setup(self, ctx: "ApplicationContext") -> None:
        """Inisialisasi plugin dan daftarkan semua handler.

        Dipanggil sekali saat plugin pertama kali dimuat.

        Args:
            ctx: ApplicationContext berisi semua komponen sistem.

        Raises:
            PluginSetupError: Jika setup gagal.
        """

    async def teardown(self) -> None:
        """Bersihkan resource saat plugin dihentikan.

        Override jika plugin memiliki resource yang perlu dibersihkan.
        """

    @abstractmethod
    async def health_check(self) -> PluginHealth:
        """Kembalikan status kesehatan plugin.

        Returns:
            PluginHealth dengan status "healthy", "degraded", atau "unhealthy".
        """

    def __repr__(self) -> str:
        return f"<Plugin: {self.name} v{self.version}>"
