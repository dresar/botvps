"""DatabaseManager untuk mengelola koneksi aiosqlite."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import aiosqlite
import structlog

from guardian.core.exceptions import DatabaseError, QueryError

logger = structlog.get_logger(__name__)


async def _configure_connection(conn: aiosqlite.Connection) -> None:
    """Terapkan PRAGMA configuration yang direkomendasikan untuk SQLite."""
    pragmas = [
        "PRAGMA journal_mode = WAL",
        "PRAGMA synchronous = NORMAL",
        "PRAGMA cache_size = -32000",
        "PRAGMA foreign_keys = ON",
        "PRAGMA busy_timeout = 5000",
        "PRAGMA mmap_size = 134217728",
    ]
    for pragma in pragmas:
        await conn.execute(pragma)
    await conn.commit()


class DatabaseManager:
    """Mengelola koneksi ke SQLite database.

    Menyediakan akses thread-safe ke database melalui connection pool
    sederhana berbasis asyncio.

    Args:
        db_path: Path ke file database SQLite.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Buka koneksi database dan jalankan migrasi.

        Raises:
            DatabaseError: Jika koneksi atau migrasi gagal.
        """
        from guardian.migrations.migration_runner import run_migrations

        try:
            self._connection = await aiosqlite.connect(self._db_path)
            self._connection.row_factory = aiosqlite.Row
            await _configure_connection(self._connection)
            logger.info("Koneksi database berhasil dibuka.", path=self._db_path)
        except Exception as e:
            raise DatabaseError(
                f"Gagal membuka koneksi database: {e}", detail=str(e)
            ) from e

        try:
            await run_migrations(connection=self._connection)
        except Exception as e:
            raise DatabaseError(f"Migrasi database gagal: {e}", detail=str(e)) from e

    async def close(self) -> None:
        """Tutup koneksi database."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Koneksi database ditutup.")

    @property
    def connection(self) -> aiosqlite.Connection:
        """Dapatkan koneksi aktif.

        Raises:
            DatabaseError: Jika koneksi belum diinisialisasi.
        """
        if self._connection is None:
            raise DatabaseError("Database belum diinisialisasi. Panggil initialize() terlebih dahulu.")
        return self._connection

    async def execute(
        self, query: str, parameters: tuple[Any, ...] = ()
    ) -> aiosqlite.Cursor:
        """Eksekusi satu query.

        Args:
            query: Query SQL.
            parameters: Parameter query.

        Returns:
            Cursor hasil eksekusi.

        Raises:
            QueryError: Jika query gagal dieksekusi.
        """
        try:
            async with self._lock:
                cursor = await self.connection.execute(query, parameters)
                await self.connection.commit()
                return cursor
        except aiosqlite.Error as e:
            raise QueryError(f"Query gagal: {e}", detail=f"Query: {query}") from e

    async def execute_many(
        self, query: str, parameters_list: list[tuple[Any, ...]]
    ) -> None:
        """Eksekusi query dengan banyak parameter (batch).

        Args:
            query: Query SQL.
            parameters_list: List parameter untuk setiap eksekusi.

        Raises:
            QueryError: Jika query gagal.
        """
        try:
            async with self._lock:
                await self.connection.executemany(query, parameters_list)
                await self.connection.commit()
        except aiosqlite.Error as e:
            raise QueryError(f"Batch query gagal: {e}") from e

    async def fetch_one(
        self, query: str, parameters: tuple[Any, ...] = ()
    ) -> aiosqlite.Row | None:
        """Ambil satu baris hasil query.

        Args:
            query: Query SQL SELECT.
            parameters: Parameter query.

        Returns:
            Baris pertama hasil atau None jika tidak ada.
        """
        try:
            async with self.connection.execute(query, parameters) as cursor:
                return await cursor.fetchone()
        except aiosqlite.Error as e:
            raise QueryError(f"Fetch one gagal: {e}", detail=f"Query: {query}") from e

    async def fetch_all(
        self, query: str, parameters: tuple[Any, ...] = ()
    ) -> list[aiosqlite.Row]:
        """Ambil semua baris hasil query.

        Args:
            query: Query SQL SELECT.
            parameters: Parameter query.

        Returns:
            List semua baris hasil.
        """
        try:
            async with self.connection.execute(query, parameters) as cursor:
                return await cursor.fetchall()
        except aiosqlite.Error as e:
            raise QueryError(f"Fetch all gagal: {e}", detail=f"Query: {query}") from e

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Context manager untuk transaksi database.

        Yields:
            Koneksi database yang aktif dalam transaksi.

        Raises:
            QueryError: Jika transaksi gagal (rollback otomatis).
        """
        async with self._lock:
            try:
                yield self.connection
                await self.connection.commit()
            except Exception as e:
                await self.connection.rollback()
                raise QueryError(
                    f"Transaksi gagal dan di-rollback: {e}"
                ) from e
