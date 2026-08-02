"""Plugin PackageProtectionPlugin — Proteksi Aplikasi Terlarang."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_plugin import BasePlugin, PluginHealth
from guardian.plugins.package_protection.handlers import PackageProtectionHandlers
from guardian.plugins.package_protection.service import PackageProtectionService

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class PackageProtectionPlugin(BasePlugin):
    """Plugin proteksi VPS dari instalasi & eksekusi aplikasi terlarang (OpenCode)."""

    def __init__(self) -> None:
        self._service: PackageProtectionService | None = None

    @property
    def name(self) -> str:
        return "package_protection"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Package Protection & OpenCode Ban Enforcer"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def setup(self, ctx: "ApplicationContext") -> None:
        """Daftarkan service, handler, startup scanner, dan scheduled scanner."""
        self._service = PackageProtectionService(ctx)
        handlers = PackageProtectionHandlers(self._service)

        for ns in ("package_guard", "package_guard_status", "package_protection", "package"):
            for cmd_name in ("menu", "status", "list", "scan"):
                try:
                    ctx.plugin_manager.register_command(
                        namespace=ns,
                        command=cmd_name,
                        handler=handlers.handle_package_guard,
                        permissions=["system:read"],
                        description="Proteksi VPS dari Paket Terlarang",
                    )
                except Exception:
                    pass

        # 1. Startup Scanner: Jalankan pemindaian otomatis saat bot menyala / VPS reboot
        asyncio.create_task(self._run_startup_scan())

        # 2. Scheduled Scanner: Pemindaian berkala (default setiap 10 menit)
        interval_min = ctx.settings.package_scan_interval_minutes
        ctx.scheduler.add_interval_job(
            job_id="package_protection.periodic_scan",
            func=self._service.run_full_scan,
            seconds=interval_min * 60,
        )

        logger.info("PackageProtectionPlugin siap.", scan_interval_minutes=interval_min)

    async def _run_startup_scan(self) -> None:
        """Jalankan startup scan setelah delay singkat saat booting."""
        await asyncio.sleep(3)
        if self._service:
            logger.info("Menjalankan Startup Scanner Package Protection...")
            await self._service.run_full_scan()

    async def health_check(self) -> PluginHealth:
        """Cek kesehatan plugin."""
        status = "healthy" if self._service and self._service.is_enabled else "degraded"
        return PluginHealth(
            plugin_name=self.name,
            status=status,
            message="Package Protection Monitoring Aktif." if status == "healthy" else "Package Protection Nonaktif.",
            checked_at=datetime.utcnow(),
        )
