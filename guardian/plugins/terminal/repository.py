"""Repository untuk Terminal Plugin — SQLite storage untuk sesi & histori."""

import time
from typing import TYPE_CHECKING

import aiosqlite
import structlog

from guardian.plugins.terminal.models import CommandHistoryDTO, TerminalSessionDTO

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager

logger = structlog.get_logger(__name__)

DEFAULT_CWD = "/"
MAX_HISTORY = 100


class TerminalRepository:
    """Akses data SQLite untuk terminal sessions & history."""

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db

    @property
    def _conn(self) -> aiosqlite.Connection:
        return self._db.connection

    # ------------------------------------------------------------------ session

    async def get_session(self, user_id: int) -> TerminalSessionDTO | None:
        """Ambil sesi terminal aktif milik user."""
        async with self._conn.execute(
            "SELECT user_id, cwd, last_active FROM terminal_sessions WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        return TerminalSessionDTO(
            user_id=row["user_id"],
            cwd=row["cwd"],
            last_active=row["last_active"],
        )

    async def upsert_session(self, user_id: int, cwd: str) -> None:
        """Buat atau perbarui sesi terminal untuk user."""
        now = time.time()
        await self._conn.execute(
            """
            INSERT INTO terminal_sessions (user_id, cwd, last_active)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                cwd         = excluded.cwd,
                last_active = excluded.last_active
            """,
            (user_id, cwd, now),
        )
        await self._conn.commit()

    async def delete_session(self, user_id: int) -> None:
        """Hapus sesi terminal user (reset ke default)."""
        await self._conn.execute(
            "DELETE FROM terminal_sessions WHERE user_id = ?", (user_id,)
        )
        await self._conn.commit()

    # ----------------------------------------------------------------- history

    async def save_history(self, user_id: int, command: str, exit_code: int) -> None:
        """Simpan riwayat perintah yang dieksekusi."""
        now = time.time()
        await self._conn.execute(
            "INSERT INTO terminal_history (user_id, command, exit_code, executed_at) VALUES (?, ?, ?, ?)",
            (user_id, command, exit_code, now),
        )
        # Hapus riwayat lama jika melebihi MAX_HISTORY
        await self._conn.execute(
            """
            DELETE FROM terminal_history
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM terminal_history WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
            )
            """,
            (user_id, user_id, MAX_HISTORY),
        )
        await self._conn.commit()

    async def get_history(self, user_id: int, limit: int = 20) -> list[CommandHistoryDTO]:
        """Ambil riwayat N perintah terakhir user."""
        async with self._conn.execute(
            """
            SELECT id, user_id, command, exit_code, executed_at
            FROM terminal_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [
            CommandHistoryDTO(
                id=r["id"],
                user_id=r["user_id"],
                command=r["command"],
                exit_code=r["exit_code"],
                executed_at=r["executed_at"],
            )
            for r in rows
        ]

    async def clear_history(self, user_id: int) -> int:
        """Hapus semua riwayat user. Kembalikan jumlah baris yang dihapus."""
        cur = await self._conn.execute(
            "DELETE FROM terminal_history WHERE user_id = ?", (user_id,)
        )
        await self._conn.commit()
        return cur.rowcount or 0
