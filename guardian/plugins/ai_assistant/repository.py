"""Repository untuk ai_assistant Hermes Memory System, Gemini & Groq Key Pool, serta Skill Engine."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from guardian.interfaces.base_repository import BaseRepository
from guardian.plugins.ai_assistant.models import AIChatMessageDTO, AIMemoryDTO

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class AIMemoryRepository(BaseRepository):
    """Repository database SQLite untuk memori, histori AI, Key Pool, dan Hermes Dynamic Skill Engine."""

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
        """Tambah 1 hingga 100+ API Key ke SQLite Key Pool (Bulk Insert)."""
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
        """Ambil API Key Gemini aktif berikutnya dari SQLite."""
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
        """Catat sukses pemakaian API key."""
        now_str = datetime.utcnow().isoformat()
        await self._db.execute(
            """UPDATE gemini_api_keys
               SET usage_count = usage_count + 1, last_used_at = ?
               WHERE api_key = ?""",
            (now_str, api_key),
        )

    async def record_key_error(self, api_key: str, error_msg: str, status_code: int = 0) -> None:
        """Catat error pemakaian Gemini API key."""
        now_str = datetime.utcnow().isoformat()
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
        """Ambil statistik lengkap Gemini Key Pool."""
        total_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM gemini_api_keys")
        active_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM gemini_api_keys WHERE is_active = 1")
        inactive_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM gemini_api_keys WHERE is_active = 0")
        usage_row = await self._db.fetch_one("SELECT SUM(usage_count) as total_use FROM gemini_api_keys")

        return {
            "total_keys": total_row["cnt"] if total_row else 0,
            "active_keys": active_row["cnt"] if active_row else 0,
            "inactive_keys": inactive_row["cnt"] if inactive_row else 0,
            "total_usage": usage_row["total_use"] if usage_row and usage_row["total_use"] else 0,
        }

    async def delete_key(self, key_or_id: str) -> bool:
        """Hapus API Key dari SQLite."""
        clean = key_or_id.strip()
        if clean.isdigit():
            cursor = await self._db.execute("DELETE FROM gemini_api_keys WHERE id = ?", (int(clean),))
        else:
            cursor = await self._db.execute("DELETE FROM gemini_api_keys WHERE api_key = ?", (clean,))
        return cursor.rowcount > 0

    async def clear_inactive_keys(self) -> int:
        """Hapus seluruh Gemini API Key mati."""
        cursor = await self._db.execute("DELETE FROM gemini_api_keys WHERE is_active = 0")
        return cursor.rowcount

    # ---- GROQ AI BACKUP POOL ----

    async def add_groq_keys(self, keys: list[str], model: str = "llama-3.3-70b-versatile") -> tuple[int, int]:
        """Tambah Groq API Key ke SQLite pool."""
        added = 0
        duplicates = 0
        now_str = datetime.utcnow().isoformat()

        for k in keys:
            clean_key = k.strip()
            if not clean_key:
                continue
            cursor = await self._db.execute(
                """INSERT OR IGNORE INTO groq_api_keys (api_key, model, is_active, created_at)
                   VALUES (?, ?, 1, ?)""",
                (clean_key, model, now_str),
            )
            if cursor.rowcount > 0:
                added += 1
            else:
                duplicates += 1

        return added, duplicates

    async def get_next_groq_key(self) -> tuple[str, str] | tuple[None, None]:
        """Ambil (api_key, model) Groq aktif berikutnya dari SQLite."""
        row = await self._db.fetch_one(
            """SELECT api_key, model FROM groq_api_keys
               WHERE is_active = 1
               ORDER BY last_used_at IS NULL DESC, last_used_at ASC, usage_count ASC
               LIMIT 1"""
        )
        if row:
            return row["api_key"], row["model"]
        return None, None

    async def record_groq_success(self, api_key: str) -> None:
        """Catat sukses pemakaian Groq API key."""
        now_str = datetime.utcnow().isoformat()
        await self._db.execute(
            """UPDATE groq_api_keys
               SET usage_count = usage_count + 1, last_used_at = ?
               WHERE api_key = ?""",
            (now_str, api_key),
        )

    async def record_groq_error(self, api_key: str, error_msg: str, status_code: int = 0) -> None:
        """Catat error Groq API key."""
        now_str = datetime.utcnow().isoformat()
        disable = 1 if (status_code in (400, 401, 403, 404, 429) or "quota" in error_msg.lower() or "limit" in error_msg.lower()) else 0

        if disable:
            await self._db.execute(
                """UPDATE groq_api_keys
                   SET error_count = error_count + 1, last_error = ?, is_active = 0, last_used_at = ?
                   WHERE api_key = ?""",
                (error_msg[:255], now_str, api_key),
            )
        else:
            await self._db.execute(
                """UPDATE groq_api_keys
                   SET error_count = error_count + 1, last_error = ?, last_used_at = ?
                   WHERE api_key = ?""",
                (error_msg[:255], now_str, api_key),
            )

    async def get_groq_stats(self) -> dict[str, Any]:
        """Ambil statistik Groq Key Pool."""
        total_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM groq_api_keys")
        active_row = await self._db.fetch_one("SELECT COUNT(*) as cnt FROM groq_api_keys WHERE is_active = 1")
        usage_row = await self._db.fetch_one("SELECT SUM(usage_count) as total_use FROM groq_api_keys")

        return {
            "total_keys": total_row["cnt"] if total_row else 0,
            "active_keys": active_row["cnt"] if active_row else 0,
            "total_usage": usage_row["total_use"] if usage_row and usage_row["total_use"] else 0,
        }

    async def delete_groq_key(self, key_or_id: str) -> bool:
        """Hapus Groq API Key dari SQLite."""
        clean = key_or_id.strip()
        if clean.isdigit():
            cursor = await self._db.execute("DELETE FROM groq_api_keys WHERE id = ?", (int(clean),))
        else:
            cursor = await self._db.execute("DELETE FROM groq_api_keys WHERE api_key = ?", (clean,))
        return cursor.rowcount > 0

    async def clear_inactive_groq_keys(self) -> int:
        """Hapus seluruh Groq API Key mati atau error."""
        cursor = await self._db.execute("DELETE FROM groq_api_keys WHERE is_active = 0 OR error_count > 0")
        return cursor.rowcount

    async def get_all_gemini_keys(self, limit: int = 50) -> list[dict[str, Any]]:
        """Ambil daftar Gemini API Key beserta ID, error_count, dan status."""
        rows = await self._db.fetch_all(
            """SELECT id, api_key, usage_count, error_count, is_active, last_error
               FROM gemini_api_keys
               ORDER BY is_active DESC, error_count ASC, id ASC
               LIMIT ?""",
            (limit,),
        )
        return [
            {
                "id": r["id"],
                "api_key_masked": r["api_key"][:10] + "..." + r["api_key"][-4:] if len(r["api_key"]) > 14 else r["api_key"],
                "usage_count": r["usage_count"],
                "error_count": r["error_count"],
                "is_active": r["is_active"],
                "last_error": r["last_error"],
            }
            for r in rows
        ]

    async def get_all_groq_keys(self, limit: int = 50) -> list[dict[str, Any]]:
        """Ambil daftar Groq API Key beserta ID, error_count, dan status."""
        rows = await self._db.fetch_all(
            """SELECT id, api_key, usage_count, error_count, is_active, last_error
               FROM groq_api_keys
               ORDER BY is_active DESC, error_count ASC, id ASC
               LIMIT ?""",
            (limit,),
        )
        return [
            {
                "id": r["id"],
                "api_key_masked": r["api_key"][:10] + "..." + r["api_key"][-4:] if len(r["api_key"]) > 14 else r["api_key"],
                "usage_count": r["usage_count"],
                "error_count": r["error_count"],
                "is_active": r["is_active"],
                "last_error": r["last_error"],
            }
            for r in rows
        ]

    # ---- HERMES DYNAMIC SKILL ENGINE ----

    async def add_skill(
        self, skill_name: str, instructions: str, description: str = "", trigger_words: str = ""
    ) -> dict[str, Any]:
        """Tambah skill AI baru ke SQLite."""
        now_str = datetime.utcnow().isoformat()
        cursor = await self._db.execute(
            """INSERT INTO ai_skills (skill_name, description, trigger_words, instructions, is_active, created_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (skill_name.strip(), description.strip(), trigger_words.strip(), instructions.strip(), now_str),
        )
        return {
            "id": cursor.lastrowid,
            "skill_name": skill_name.strip(),
            "description": description.strip(),
            "instructions": instructions.strip(),
        }

    async def get_skills(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Ambil seluruh skill AI yang terdaftar."""
        sql = "SELECT * FROM ai_skills WHERE is_active = 1 ORDER BY id ASC" if active_only else "SELECT * FROM ai_skills ORDER BY id ASC"
        rows = await self._db.fetch_all(sql)
        return [
            {
                "id": r["id"],
                "skill_name": r["skill_name"],
                "description": r["description"],
                "trigger_words": r["trigger_words"],
                "instructions": r["instructions"],
                "is_active": r["is_active"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    async def update_skill(self, skill_id: int, instructions: str) -> bool:
        """Edit instruksi skill berdasarkan ID."""
        cursor = await self._db.execute(
            "UPDATE ai_skills SET instructions = ? WHERE id = ?",
            (instructions.strip(), skill_id),
        )
        return cursor.rowcount > 0

    async def delete_skill(self, skill_id: int) -> bool:
        """Hapus skill berdasarkan ID."""
        cursor = await self._db.execute("DELETE FROM ai_skills WHERE id = ?", (skill_id,))
        return cursor.rowcount > 0

    async def toggle_skill(self, skill_id: int) -> bool:
        """Toggle status aktif/nonaktif skill."""
        row = await self._db.fetch_one("SELECT is_active FROM ai_skills WHERE id = ?", (skill_id,))
        if not row:
            return False
        new_status = 0 if row["is_active"] == 1 else 1
        await self._db.execute("UPDATE ai_skills SET is_active = ? WHERE id = ?", (new_status, skill_id))
        return True

    async def seed_default_skills(self, news_key: str = "", weather_key: str = "") -> None:
        """Seed default NewsAPI dan OpenWeatherMap skills ke SQLite jika belum ada."""
        existing = await self.get_skills(active_only=False)
        skill_names = {s["skill_name"].lower() for s in existing}

        if "newsapi search & headlines" not in skill_names:
            n_key = news_key or "NEWS_API_KEY"
            await self.add_skill(
                skill_name="NewsAPI Search & Headlines",
                description="Pencarian Berita Terkini & Top Headlines Dunia via NewsAPI.org",
                trigger_words="berita, news, berita terbaru, headlines, newsapi",
                instructions=f"Gunakan API Key NewsAPI ({n_key}) untuk mengambil berita terkini dari https://newsapi.org/. Jika pengguna menanyakan berita terbaru, sajikan judul, sumber, dan ringkasan singkat secara rapi.",
            )

        if "openweathermap weather forecast" not in skill_names:
            w_key = weather_key or "OPENWEATHER_API_KEY"
            await self.add_skill(
                skill_name="OpenWeatherMap Weather Forecast",
                description="Pengecekan Cuaca & Prakiraan Cuaca Real-time via OpenWeatherMap",
                trigger_words="cuaca, weather, prakiraan cuaca, suhu, hujan, openweathermap",
                instructions=f"Gunakan API Key OpenWeatherMap ({w_key}) untuk mengambil data cuaca real-time dari https://api.openweathermap.org/. Jika pengguna menanyakan cuaca, sajikan suhu (°C), kelembapan, dan kondisi cuaca secara akurat.",
            )

    async def sync_neon_database(self, neon_url: str) -> bool:
        """Sinkronisasi data SQLite Key Pool & Memori ke Secondary Backup Database Neon PostgreSQL."""
        if not neon_url:
            return False
        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(neon_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """CREATE TABLE IF NOT EXISTS neon_ai_key_pool_backup (
                            id SERIAL PRIMARY KEY,
                            api_key TEXT UNIQUE NOT NULL,
                            provider VARCHAR(50) DEFAULT 'gemini',
                            is_active INT DEFAULT 1,
                            usage_count INT DEFAULT 0,
                            error_count INT DEFAULT 0,
                            last_error TEXT,
                            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );"""
                    )
                    gemini_keys = await self.get_all_gemini_keys(limit=100)
                    for k in gemini_keys:
                        await cur.execute(
                            """INSERT INTO neon_ai_key_pool_backup (api_key, provider, is_active, usage_count, error_count, last_error)
                               VALUES (%s, 'gemini', %s, %s, %s, %s)
                               ON CONFLICT (api_key) DO UPDATE
                               SET usage_count = EXCLUDED.usage_count, error_count = EXCLUDED.error_count, is_active = EXCLUDED.is_active;""",
                            (k["api_key_masked"], k["is_active"], k["usage_count"], k["error_count"], k.get("last_error", "")),
                        )
                    await conn.commit()
            return True
        except Exception as e:
            import structlog
            structlog.get_logger(__name__).warning("Neon PostgreSQL backup sync gagal atau terlewati.", error=str(e))
            return False
