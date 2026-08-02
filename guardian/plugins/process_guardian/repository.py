"""Repository untuk process_guardian plugin."""

from datetime import datetime
from typing import TYPE_CHECKING

from guardian.interfaces.base_repository import BaseRepository
from guardian.plugins.process_guardian.models import CPUGuardHistoryDTO, CPUGuardRuleDTO

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class CPUGuardRepository(BaseRepository):
    """Repository akses database SQLite untuk CPU Guard."""

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db

    async def add_history(self, history: CPUGuardHistoryDTO) -> None:
        """Catat histori tindakan kill/warning."""
        await self._db.execute(
            """INSERT INTO cpu_kill_history
               (pid, process_name, username, cpu_percent, memory_percent, cmdline, running_time, action_taken, status, reason, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                history.pid,
                history.process_name,
                history.username,
                history.cpu_percent,
                history.memory_percent,
                history.cmdline,
                history.running_time,
                history.action_taken,
                history.status,
                history.reason,
                history.executed_at.isoformat(),
            ),
        )

    async def get_history(self, limit: int = 20) -> list[CPUGuardHistoryDTO]:
        """Ambil histori tindakan terbaru."""
        rows = await self._db.fetch_all(
            "SELECT * FROM cpu_kill_history ORDER BY id DESC LIMIT ?", (limit,)
        )
        results = []
        for r in rows:
            results.append(
                CPUGuardHistoryDTO(
                    id=r["id"],
                    pid=r["pid"],
                    process_name=r["process_name"],
                    username=r["username"],
                    cpu_percent=r["cpu_percent"],
                    memory_percent=r["memory_percent"],
                    cmdline=r["cmdline"],
                    running_time=r["running_time"],
                    action_taken=r["action_taken"],
                    status=r["status"],
                    reason=r["reason"],
                    executed_at=datetime.fromisoformat(r["executed_at"]),
                )
            )
        return results

    async def count_today_kills(self) -> int:
        """Hitung jumlah tindakan kill hari ini."""
        row = await self._db.fetch_one(
            """SELECT COUNT(*) as cnt FROM cpu_kill_history
               WHERE status = 'success' AND action_taken IN ('SIGTERM', 'SIGKILL')
               AND date(executed_at) = date('now', 'utc')"""
        )
        return row["cnt"] if row else 0

    async def add_rule(self, rule_type: str, value: str, added_by: int) -> bool:
        """Tambah aturan whitelist / blacklist."""
        try:
            await self._db.execute(
                "INSERT INTO cpu_guard_rules (rule_type, value, added_by) VALUES (?, ?, ?)",
                (rule_type, value.lower().strip(), added_by),
            )
            return True
        except Exception:
            return False

    async def remove_rule(self, rule_type: str, value: str) -> bool:
        """Hapus aturan whitelist / blacklist."""
        cursor = await self._db.execute(
            "DELETE FROM cpu_guard_rules WHERE rule_type = ? AND value = ?",
            (rule_type, value.lower().strip()),
        )
        return cursor.rowcount > 0

    async def get_rules(self, rule_type: str) -> list[str]:
        """Ambil daftar aturan whitelist / blacklist."""
        rows = await self._db.fetch_all(
            "SELECT value FROM cpu_guard_rules WHERE rule_type = ?", (rule_type,)
        )
        return [r["value"] for r in rows]
