"""Repository untuk ai_assistant Hermes Memory System."""

from datetime import datetime
from typing import TYPE_CHECKING

from guardian.interfaces.base_repository import BaseRepository
from guardian.plugins.ai_assistant.models import AIChatMessageDTO, AIMemoryDTO

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class AIMemoryRepository(BaseRepository):
    """Repository database SQLite untuk memori & histori AI."""

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db

    async def add_memory(self, telegram_id: int, content: str, memory_type: str = "rule") -> AIMemoryDTO:
        """Simpan memori jangka panjang / aturan baru."""
        cursor = await self._db.execute(
            """INSERT INTO ai_memories (telegram_id, memory_type, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (telegram_id, memory_type, content.strip(), datetime.utcnow().isoformat()),
        )
        return AIMemoryDTO(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            memory_type=memory_type,
            content=content.strip(),
            created_at=datetime.utcnow(),
        )

    async def get_memories(self, telegram_id: int) -> list[AIMemoryDTO]:
        """Ambil seluruh memori / aturan pengguna."""
        rows = await self._db.fetch_all(
            "SELECT * FROM ai_memories WHERE telegram_id = ? ORDER BY id ASC",
            (telegram_id,),
        )
        return [
            AIMemoryDTO(
                id=r["id"],
                telegram_id=r["telegram_id"],
                memory_type=r["memory_type"],
                content=r["content"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]

    async def delete_memory(self, telegram_id: int, memory_id: int) -> bool:
        """Hapus memori spesifik berdasarkan ID."""
        cursor = await self._db.execute(
            "DELETE FROM ai_memories WHERE telegram_id = ? AND id = ?",
            (telegram_id, memory_id),
        )
        return cursor.rowcount > 0

    async def clear_memories(self, telegram_id: int) -> int:
        """Hapus seluruh memori pengguna."""
        cursor = await self._db.execute(
            "DELETE FROM ai_memories WHERE telegram_id = ?",
            (telegram_id,),
        )
        return cursor.rowcount

    async def add_chat_turn(self, telegram_id: int, role: str, content: str) -> None:
        """Simpan satu giliran percakapan ke histori percakapan (Short-Term Memory)."""
        await self._db.execute(
            """INSERT INTO ai_chat_history (telegram_id, role, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (telegram_id, role, content.strip(), datetime.utcnow().isoformat()),
        )

    async def get_recent_chat_history(self, telegram_id: int, limit: int = 10) -> list[AIChatMessageDTO]:
        """Ambil N percakapan terakhir pengguna."""
        rows = await self._db.fetch_all(
            """SELECT * FROM (
                SELECT * FROM ai_chat_history WHERE telegram_id = ? ORDER BY id DESC LIMIT ?
               ) ORDER BY id ASC""",
            (telegram_id, limit),
        )
        return [
            AIChatMessageDTO(
                id=r["id"],
                telegram_id=r["telegram_id"],
                role=r["role"],
                content=r["content"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]

    async def clear_chat_history(self, telegram_id: int) -> int:
        """Kosongkan histori percakapan (Reset Short-Term Memory)."""
        cursor = await self._db.execute(
            "DELETE FROM ai_chat_history WHERE telegram_id = ?",
            (telegram_id,),
        )
        return cursor.rowcount
