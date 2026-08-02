"""Migration runner untuk mengelola versi skema database."""

import re
from pathlib import Path

import aiosqlite
import structlog

from guardian.core.exceptions import MigrationError

logger = structlog.get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent


def _get_migration_version(filename: str) -> int | None:
    """Ekstrak nomor versi dari nama file migrasi."""
    match = re.match(r"^(\d{4})_.*\.sql$", filename)
    if match:
        return int(match.group(1))
    return None


def _discover_migrations() -> list[tuple[int, Path]]:
    """Temukan semua file migrasi di direktori migrations/, urutkan berdasarkan versi."""
    migrations = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        version = _get_migration_version(path.name)
        if version is not None:
            migrations.append((version, path))
    return sorted(migrations, key=lambda x: x[0])


async def _get_applied_versions(conn: aiosqlite.Connection) -> set[int]:
    """Dapatkan semua versi migrasi yang sudah diterapkan."""
    try:
        async with conn.execute(
            "SELECT version FROM migrations ORDER BY version"
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
    except aiosqlite.OperationalError:
        return set()


async def _apply_migration(conn: aiosqlite.Connection, version: int, path: Path) -> None:
    """Terapkan satu file migrasi dalam transaksi."""
    sql_content = path.read_text(encoding="utf-8")

    try:
        async with conn.execute("BEGIN"):
            pass

        for statement in sql_content.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                await conn.execute(stmt)

        await conn.execute(
            "INSERT INTO migrations (version, name) VALUES (?, ?)",
            (version, path.stem),
        )
        await conn.commit()
        logger.info("Migrasi diterapkan", version=version, name=path.stem)
    except Exception as e:
        await conn.rollback()
        raise MigrationError(
            f"Gagal menerapkan migrasi {version}: {e}",
            detail=str(e),
        ) from e


async def run_migrations(db_path: str) -> None:
    """Jalankan semua migrasi yang belum diterapkan.

    Args:
        db_path: Path ke file database SQLite.

    Raises:
        MigrationError: Jika migrasi gagal dijalankan.
    """
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = OFF")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                version     INTEGER NOT NULL UNIQUE,
                name        TEXT    NOT NULL,
                applied_at  TEXT    NOT NULL DEFAULT (datetime('now', 'utc'))
            )
        """)
        await conn.commit()

        applied = await _get_applied_versions(conn)
        all_migrations = _discover_migrations()
        pending = [(v, p) for v, p in all_migrations if v not in applied]

        if not pending:
            logger.debug("Tidak ada migrasi baru yang perlu diterapkan.")
            return

        logger.info("Menjalankan migrasi database...", count=len(pending))

        for version, path in pending:
            await _apply_migration(conn, version, path)

        await conn.execute("PRAGMA foreign_keys = ON")
        logger.info("Semua migrasi selesai.", total_applied=len(pending))
