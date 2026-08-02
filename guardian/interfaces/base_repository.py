"""Abstract class BaseRepository — semua repository harus mewarisi class ini."""

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager


class BaseRepository(ABC):
    """Abstract class dasar untuk semua repository.

    Repository adalah lapisan akses data. Setiap repository bertanggung
    jawab atas CRUD untuk satu entitas database.

    Repository menerima DatabaseManager sebagai dependensi melalui
    konstruktor (dependency injection).

    Args:
        db: DatabaseManager untuk akses ke database.
    """

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db
