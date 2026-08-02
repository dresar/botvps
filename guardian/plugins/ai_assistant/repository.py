"""Repository untuk ai_assistant Hermes Memory System & Gemini API Key Pool."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from guardian.interfaces.base_repository import BaseRepository
from guardian.plugins.ai_assistant.models import AIChatMessageDTO, AIMemoryDTO

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class AIMemoryRepository(BaseRepository):
    """Repository database SQLite untuk memori, histori AI, dan Gemini API Key Pool."""

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db

    # ---- HERMES MEMORY SYSTEM ----

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

    # ---- GEMINI API KEY POOL MANAGEMENT ----

    async def add_api_keys(self, keys: list[str]) -> tuple[int, int]:
        """Tambah 1 hingga 100+ API Key ke SQLite Key Pool (Bulk Insert).

        Returns:
            Tuple (jumlah_ditambahkan, jumlah_duplikat).
        """
        added = 0
        duplicates = 0
        now_str = datetime.utcnow().isoformat()

        for k in keys:
            clean_key = k.strip()
            if not clean_key:
                continue
            cursor = await self._db.execute(
                """INSERT OR IGNORE INTO gemini_api_keys (api_key, is_active, created_at)
                   VALUES (?, 1, ?)""",
                (clean_key, now_str),
            )
            if cursor.rowcount > 0:
                added += 1
            else:
                duplicates += 1

        return added, duplicates

    async def get_next_active_key(self) -> str | None:
        """Ambil API Key aktif berikutnya dari SQLite dengan algoritma LRU/Round-Robin."""
        row = await self._db.fetch_one(
            """SELECT api_key FROM gemini_api_keys
               WHERE is_active = 1
               ORDER BY last_used_at IS NULL DESC, last_used_at ASC, usage_count ASC
               LIMIT 1"""
        )
        if row:
            return row["api_key"]
        return None

    async def record_key_success(self, api_key: str) -> None:
        """Catat sukses pemakaian API key (update usage_count & last_used_at)."""
        now_str = datetime.utcnow().isoformat()
        await self._db.execute(
            """UPDATE gemini_api_keys
               SET usage_count = usage_count + 1, last_used_at = ?
               WHERE api_key = ?""",
            (now_str, api_key),
        )

    async def record_key_error(self, api_key: str, error_msg: str, status_code: int = 0) -> None:
        """Catat error pemakaian API key. Jika quota habis (429/403/400) atau error >= 3, dinonaktifkan."""
        now_str = datetime.utcnow().isoformat()

        # Otomatis nonaktifkan key jika status HTTP menunjukkan kuota habis atau invalid key
        disable = 1 if (status_code in (400, 401, 403, 404, 429) or "quota" in error_msg.lower() or "limit" in error_msg.lower()) else 0

        if disable:
            await self._db.execute(
                """UPDATE gemini_api_keys
                   SET error_count = error_count + 1, last_error = ?, is_active = 0, last_used_at = ?
                   WHERE api_key = ?""",
                (error_msg[:255], now_str, api_key),
            )
        else:
            await self._db.execute(
                """UPDATE gemini_api_keys
                   SET error_count = error_count + 1, last_error = ?, last_used_at = ?
                   WHERE api_key = ?""",
                (error_msg[:255], now_str, api_key),
            )

    async def get_keys_stats(self) -> dict[str, Any]:
        """Ambil statistik lengkap Key Pool di SQLite."""
        total_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM gemini_api_keys")
        active_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM gemini_api_keys WHERE is_active = 1")
        inactive_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM gemini_api_keys WHERE is_active = 0")
        usage_row = await self._db.fetch_one("SELECT SUM(usage_count) as total_use FROM gemini_api_keys")

        total = total_row["cnt"] if total_row else 0
        active = active_row["cnt"] if active_row else 0
        inactive = inactive_row["cnt"] if inactive_row else 0
        total_usage = usage_row["total_use"] if usage_row and usage_row["total_use"] else 0

        return {
            "total_keys": total,
            "active_keys": active,
            "inactive_keys": inactive,
            "total_usage": total_usage,
        }

    async def delete_key(self, key_or_id: str) -> bool:
        """Hapus API Key dari SQLite berdasarkan ID atau string Key."""
        clean = key_or_id.strip()
        if clean.isdigit():
            cursor = await self._db.execute(
                "DELETE FROM gemini_api_keys WHERE id = ?",
                (int(clean),),
            )
        else:
            cursor = await self._db.execute(
                "DELETE FROM gemini_api_keys WHERE api_key = ?",
                (clean,),
            )
        return cursor.rowcount > 0

    async def clear_inactive_keys(self) -> int:
        """Hapus seluruh API Key yang sudah dinonaktifkan (is_active = 0)."""
        cursor = await self._db.execute("DELETE FROM gemini_api_keys WHERE is_active = 0")
        return cursor.rowcount
