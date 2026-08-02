"""Repository untuk tabel users dan audit_logs."""

from datetime import datetime
from typing import TYPE_CHECKING

from guardian.core.auth_service import UserDTO
from guardian.interfaces.base_repository import BaseRepository

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class UserRepository(BaseRepository):
    """Akses data untuk tabel users.

    Args:
        db: DatabaseManager.
    """

    async def find_by_telegram_id(self, telegram_id: int) -> UserDTO | None:
        """Cari user berdasarkan Telegram ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return self._to_dto(row) if row else None

    async def find_all(self) -> list[UserDTO]:
        """Dapatkan semua user."""
        rows = await self._db.fetch_all(
            "SELECT * FROM users ORDER BY role, full_name"
        )
        return [self._to_dto(r) for r in rows]

    async def find_active(self) -> list[UserDTO]:
        """Dapatkan semua user aktif."""
        rows = await self._db.fetch_all(
            "SELECT * FROM users WHERE is_active = 1 ORDER BY role, full_name"
        )
        return [self._to_dto(r) for r in rows]

    async def count_all(self) -> int:
        """Hitung total semua user."""
        row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM users")
        return row["cnt"] if row else 0  # type: ignore[index]

    @staticmethod
    def _to_dto(row: object) -> UserDTO:
        """Konversi database row ke UserDTO."""
        return UserDTO(
            id=row["id"],  # type: ignore[index]
            telegram_id=row["telegram_id"],  # type: ignore[index]
            username=row["username"],  # type: ignore[index]
            full_name=row["full_name"],  # type: ignore[index]
            role=row["role"],  # type: ignore[index]
            is_active=bool(row["is_active"]),  # type: ignore[index]
            is_blocked=bool(row["is_blocked"]),  # type: ignore[index]
            alert_enabled=bool(row["alert_enabled"]),  # type: ignore[index]
            created_at=datetime.fromisoformat(row["created_at"]),  # type: ignore[index]
        )


class AuditLogRepository(BaseRepository):
    """Akses data untuk tabel audit_logs.

    Args:
        db: DatabaseManager.
    """

    async def create(
        self,
        telegram_id: int,
        action: str,
        target: str | None = None,
        parameters: str | None = None,
        user_id: int | None = None,
    ) -> int:
        """Buat record audit log baru.

        Args:
            telegram_id: Telegram ID user.
            action: Nama tindakan.
            target: Target tindakan.
            parameters: Parameter JSON.
            user_id: Internal user ID.

        Returns:
            ID record yang baru dibuat.
        """
        cursor = await self._db.execute(
            """INSERT INTO audit_logs (user_id, telegram_id, action, target, parameters, result_status)
               VALUES (?, ?, ?, ?, ?, 'pending')""",
            (user_id, telegram_id, action, target, parameters),
        )
        return cursor.lastrowid or 0

    async def update_result(
        self,
        log_id: int,
        result_status: str,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Perbarui hasil audit log.

        Args:
            log_id: ID record.
            result_status: success, failed, atau denied.
            error_message: Pesan error jika gagal.
            duration_ms: Durasi eksekusi dalam milidetik.
        """
        await self._db.execute(
            """UPDATE audit_logs SET result_status = ?, error_message = ?, duration_ms = ?
               WHERE id = ?""",
            (result_status, error_message, duration_ms, log_id),
        )

    async def find_recent(self, limit: int = 20) -> list[dict]:
        """Dapatkan audit log terbaru.

        Args:
            limit: Jumlah maksimum record.

        Returns:
            List dict audit log.
        """
        rows = await self._db.fetch_all(
            """SELECT al.*, u.full_name, u.username
               FROM audit_logs al
               LEFT JOIN users u ON al.user_id = u.id
               ORDER BY al.created_at DESC
               LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in rows]

    async def find_by_user(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """Dapatkan audit log berdasarkan user.

        Args:
            user_id: Internal user ID.
            limit: Jumlah maksimum record.
            offset: Offset untuk pagination.

        Returns:
            List dict audit log.
        """
        rows = await self._db.fetch_all(
            """SELECT * FROM audit_logs WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        )
        return [dict(row) for row in rows]

    async def count_user_commands(self, telegram_id: int, window_seconds: int) -> int:
        """Hitung jumlah command user dalam window waktu tertentu.

        Args:
            telegram_id: Telegram User ID.
            window_seconds: Window waktu dalam detik.

        Returns:
            Jumlah command.
        """
        row = await self._db.fetch_one(
            """SELECT COUNT(*) as cnt FROM audit_logs
               WHERE telegram_id = ?
               AND created_at >= datetime('now', ? || ' seconds', 'utc')""",
            (telegram_id, f"-{window_seconds}"),
        )
        return row["cnt"] if row else 0  # type: ignore[index]
