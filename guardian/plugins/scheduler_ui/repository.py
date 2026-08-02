"""Repository SQLite untuk AI Cron Scheduler Engine."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from guardian.interfaces.base_repository import BaseRepository

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class AISchedulerRepository(BaseRepository):
    """Repository database SQLite untuk AI Cron Scheduled Tasks & Reminders."""

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db

    async def add_task(
        self,
        telegram_id: int,
        task_type: str,
        message: str,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        run_at: str | None = None,
    ) -> dict[str, Any]:
        """Tambah jadwal pengingat / cron job baru ke SQLite."""
        now_str = datetime.utcnow().isoformat()
        cursor = await self._db.execute(
            """INSERT INTO ai_scheduled_tasks
               (telegram_id, task_type, cron_expression, interval_seconds, run_at, message, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                telegram_id,
                task_type,
                cron_expression,
                interval_seconds,
                run_at,
                message.strip(),
                now_str,
            ),
        )
        return {
            "id": cursor.lastrowid,
            "telegram_id": telegram_id,
            "task_type": task_type,
            "cron_expression": cron_expression,
            "interval_seconds": interval_seconds,
            "run_at": run_at,
            "message": message.strip(),
            "created_at": now_str,
        }

    async def get_active_tasks(self) -> list[dict[str, Any]]:
        """Ambil seluruh jadwal pengingat aktif."""
        rows = await self._db.fetch_all(
            "SELECT * FROM ai_scheduled_tasks WHERE is_active = 1 ORDER BY id ASC"
        )
        return [dict(r) for r in rows]

    async def update_last_run(self, task_id: int, deactivate_one_shot: bool = False) -> None:
        """Update timestamp eksekusi terakhir. Matikan jika one_shot."""
        now_str = datetime.utcnow().isoformat()
        if deactivate_one_shot:
            await self._db.execute(
                "UPDATE ai_scheduled_tasks SET last_run_at = ?, is_active = 0 WHERE id = ?",
                (now_str, task_id),
            )
        else:
            await self._db.execute(
                "UPDATE ai_scheduled_tasks SET last_run_at = ? WHERE id = ?",
                (now_str, task_id),
            )

    async def delete_task(self, task_id: int) -> bool:
        """Hapus jadwal berdasarkan ID."""
        cursor = await self._db.execute(
            "DELETE FROM ai_scheduled_tasks WHERE id = ?", (task_id,)
        )
        return cursor.rowcount > 0
