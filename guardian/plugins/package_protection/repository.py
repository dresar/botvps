"""Repository untuk package_protection plugin."""

from datetime import datetime
from typing import TYPE_CHECKING

from guardian.interfaces.base_repository import BaseRepository
from guardian.plugins.package_protection.models import BlockedPackageDTO, UninstallReportDTO

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class PackageProtectionRepository(BaseRepository):
    """Repository database SQLite untuk Package Protection."""

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db

    async def add_report(self, report: UninstallReportDTO) -> None:
        """Simpan laporan uninstall / pembersihan paket."""
        await self._db.execute(
            """INSERT INTO package_guard_logs
               (package_name, install_method, binary_location, config_location, cache_location, status, details, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.package_name,
                report.install_method,
                report.binary_location,
                report.config_location,
                report.cache_location,
                report.status,
                report.details,
                report.executed_at.isoformat(),
            ),
        )

    async def get_reports(self, limit: int = 20) -> list[UninstallReportDTO]:
        """Ambil histori laporan uninstall terbaru."""
        rows = await self._db.fetch_all(
            "SELECT * FROM package_guard_logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        results = []
        for r in rows:
            results.append(
                UninstallReportDTO(
                    id=r["id"],
                    package_name=r["package_name"],
                    install_method=r["install_method"],
                    binary_location=r["binary_location"],
                    config_location=r["config_location"],
                    cache_location=r["cache_location"],
                    status=r["status"],
                    details=r["details"],
                    executed_at=datetime.fromisoformat(r["executed_at"]),
                )
            )
        return results

    async def add_blocked_package(self, name: str, added_by: int) -> bool:
        """Tambah paket terlarang ke daftar blokir."""
        try:
            await self._db.execute(
                "INSERT INTO blocked_packages (name, added_by) VALUES (?, ?)",
                (name.lower().strip(), added_by),
            )
            return True
        except Exception:
            return False

    async def remove_blocked_package(self, name: str) -> bool:
        """Hapus paket dari daftar blokir."""
        cursor = await self._db.execute(
            "DELETE FROM blocked_packages WHERE name = ?", (name.lower().strip(),)
        )
        return cursor.rowcount > 0

    async def get_blocked_packages(self) -> list[str]:
        """Ambil daftar paket terlarang."""
        rows = await self._db.fetch_all("SELECT name FROM blocked_packages")
        return [r["name"] for r in rows]
