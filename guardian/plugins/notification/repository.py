"""Repository untuk tabel alert_configs."""

from datetime import datetime
from typing import TYPE_CHECKING

from guardian.interfaces.base_repository import BaseRepository
from guardian.plugins.notification.models import AlertConfig

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class AlertConfigRepository(BaseRepository):
    """Akses data untuk tabel alert_configs."""

    async def find_all(self) -> list[AlertConfig]:
        """Dapatkan semua konfigurasi alert."""
        rows = await self._db.fetch_all(
            "SELECT * FROM alert_configs ORDER BY metric_name"
        )
        return [self._to_model(r) for r in rows]

    async def find_active(self) -> list[AlertConfig]:
        """Dapatkan alert yang aktif."""
        rows = await self._db.fetch_all(
            "SELECT * FROM alert_configs WHERE is_active = 1"
        )
        return [self._to_model(r) for r in rows]

    async def find_by_id(self, alert_id: int) -> AlertConfig | None:
        """Cari alert berdasarkan ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM alert_configs WHERE id = ?", (alert_id,)
        )
        return self._to_model(row) if row else None

    async def update_triggered(self, alert_id: int) -> None:
        """Update waktu dan counter saat alert terpicu."""
        await self._db.execute(
            """UPDATE alert_configs
               SET last_triggered_at = ?, trigger_count = trigger_count + 1, updated_at = ?
               WHERE id = ?""",
            (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), alert_id),
        )

    async def update_threshold(
        self, alert_id: int, threshold_value: float
    ) -> None:
        """Perbarui threshold value."""
        await self._db.execute(
            "UPDATE alert_configs SET threshold_value = ?, updated_at = ? WHERE id = ?",
            (threshold_value, datetime.utcnow().isoformat(), alert_id),
        )

    async def toggle_active(self, alert_id: int, is_active: bool) -> None:
        """Aktifkan atau nonaktifkan alert."""
        await self._db.execute(
            "UPDATE alert_configs SET is_active = ?, updated_at = ? WHERE id = ?",
            (1 if is_active else 0, datetime.utcnow().isoformat(), alert_id),
        )

    @staticmethod
    def _to_model(row: object) -> AlertConfig:
        """Konversi row ke AlertConfig."""
        last_triggered = row["last_triggered_at"]  # type: ignore[index]
        return AlertConfig(
            id=row["id"],  # type: ignore[index]
            metric_name=row["metric_name"],  # type: ignore[index]
            threshold_value=row["threshold_value"],  # type: ignore[index]
            threshold_unit=row["threshold_unit"],  # type: ignore[index]
            comparison_op=row["comparison_op"],  # type: ignore[index]
            cooldown_minutes=row["cooldown_minutes"],  # type: ignore[index]
            is_active=bool(row["is_active"]),  # type: ignore[index]
            created_by=row["created_by"],  # type: ignore[index]
            last_triggered_at=(
                datetime.fromisoformat(last_triggered) if last_triggered else None
            ),
            trigger_count=row["trigger_count"],  # type: ignore[index]
        )
