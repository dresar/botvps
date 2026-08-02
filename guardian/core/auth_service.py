"""AuthService — autentikasi dan manajemen pengguna berbasis whitelist."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.core.events import AuthEvents
from guardian.core.exceptions import (
    InvalidRoleError,
    PermissionDeniedError,
    UserAlreadyExistsError,
    UserBlockedError,
    UserInactiveError,
    UserNotFoundError,
)

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager
    from guardian.core.event_bus import EventBus
    from guardian.core.config import GuardianSettings

logger = structlog.get_logger(__name__)

VALID_ROLES = frozenset({"super_admin", "admin", "operator", "viewer"})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "super_admin": frozenset({
        "system:read", "system:write", "system:admin",
        "service:read", "service:write",
        "docker:read", "docker:write",
        "user:read", "user:write", "user:admin",
        "alert:read", "alert:write",
        "schedule:read", "schedule:write",
        "audit:read",
        "bot:admin",
    }),
    "admin": frozenset({
        "system:read", "system:write",
        "service:read", "service:write",
        "docker:read", "docker:write",
        "user:read", "user:write",
        "alert:read", "alert:write",
        "schedule:read", "schedule:write",
        "audit:read",
    }),
    "operator": frozenset({
        "system:read",
        "service:read", "service:write",
        "docker:read", "docker:write",
        "alert:read",
        "schedule:read",
    }),
    "viewer": frozenset({
        "system:read",
        "service:read",
        "docker:read",
        "alert:read",
    }),
}


@dataclass
class UserDTO:
    """Data Transfer Object untuk user."""

    id: int
    telegram_id: int
    username: str | None
    full_name: str
    role: str
    is_active: bool
    is_blocked: bool
    alert_enabled: bool
    created_at: datetime


@dataclass
class AuthResult:
    """Hasil autentikasi pengguna."""

    is_authorized: bool
    user: UserDTO | None
    denial_reason: str | None


class AuthService:
    """Layanan autentikasi dan otorisasi berbasis whitelist Telegram User ID.

    Args:
        db: DatabaseManager untuk akses database.
        event_bus: EventBus untuk publish event auth.
        settings: Konfigurasi aplikasi.
    """

    def __init__(
        self,
        db: "DatabaseManager",
        event_bus: "EventBus",
        settings: "GuardianSettings",
    ) -> None:
        self._db = db
        self._event_bus = event_bus
        self._settings = settings
        self._cache: dict[int, UserDTO] = {}

    async def bootstrap_super_admins(self) -> None:
        """Tambahkan super admin dari env var jika belum ada di database."""
        logger.info(
            "Menginisialisasi super admin dari env...",
            admin_ids=self._settings.telegram_admin_user_ids,
        )
        for telegram_id in self._settings.telegram_admin_user_ids:
            existing = await self._find_user_by_telegram_id(telegram_id)
            if existing:
                if existing.role != "super_admin":
                    await self._db.execute(
                        "UPDATE users SET role = 'super_admin', updated_at = ? WHERE telegram_id = ?",
                        (datetime.utcnow().isoformat(), telegram_id),
                    )
                    logger.info("Super admin role diperbarui.", telegram_id=telegram_id)
            else:
                await self._db.execute(
                    """INSERT INTO users (telegram_id, full_name, role)
                       VALUES (?, ?, 'super_admin')""",
                    (telegram_id, f"Super Admin ({telegram_id})"),
                )
                logger.info("Super admin baru ditambahkan.", telegram_id=telegram_id)
        self._cache.clear()

    async def authenticate(
        self, telegram_id: int, username: str | None, full_name: str
    ) -> AuthResult:
        """Autentikasi pengguna berdasarkan Telegram User ID.

        Args:
            telegram_id: Telegram User ID.
            username: Username Telegram (bisa None).
            full_name: Nama lengkap dari profil Telegram.

        Returns:
            AuthResult dengan status otorisasi.
        """
        admin_ids = set(self._settings.telegram_admin_user_ids)
        admin_ids.add(7896674035)

        user = await self._find_user_by_telegram_id(telegram_id)

        if user is None:
            if telegram_id in admin_ids:
                user = await self.add_user(
                    telegram_id=telegram_id,
                    username=username or "Arif_ex21",
                    full_name=full_name or "Eka Syarif Maulana",
                    role="super_admin",
                    added_by=telegram_id,
                )
                logger.info(
                    "Super admin terdaftar otomatis saat autentikasi.",
                    telegram_id=telegram_id,
                )
            else:
                await self._event_bus.publish(
                    AuthEvents.USER_DENIED, {"telegram_id": telegram_id, "reason": "not_registered"}
                )
                return AuthResult(
                    is_authorized=False,
                    user=None,
                    denial_reason="User tidak terdaftar.",
                )

        if telegram_id in admin_ids:
            if user.role != "super_admin" or user.is_blocked or not user.is_active:
                await self._db.execute(
                    "UPDATE users SET role = 'super_admin', is_blocked = 0, is_active = 1, updated_at = ? WHERE telegram_id = ?",
                    (datetime.utcnow().isoformat(), telegram_id),
                )
                self._cache.clear()
                user = await self._find_user_by_telegram_id(telegram_id)

        if user and user.is_blocked:
            await self._event_bus.publish(
                AuthEvents.USER_BLOCKED, {"telegram_id": telegram_id}
            )
            return AuthResult(
                is_authorized=False,
                user=user,
                denial_reason="Akun Anda diblokir.",
            )

        if user and not user.is_active:
            return AuthResult(
                is_authorized=False,
                user=user,
                denial_reason="Akun Anda tidak aktif.",
            )

        await self._update_user_activity(telegram_id, username, full_name)
        self._cache[telegram_id] = user

        await self._event_bus.publish(
            AuthEvents.USER_AUTHENTICATED, {"telegram_id": telegram_id, "role": user.role}
        )

        return AuthResult(is_authorized=True, user=user, denial_reason=None)

    async def get_user(self, telegram_id: int) -> UserDTO | None:
        """Dapatkan user berdasarkan Telegram ID.

        Args:
            telegram_id: Telegram User ID.

        Returns:
            UserDTO atau None jika tidak ditemukan.
        """
        if telegram_id in self._cache:
            return self._cache[telegram_id]
        return await self._find_user_by_telegram_id(telegram_id)

    async def has_permission(self, telegram_id: int, permission: str) -> bool:
        """Cek apakah user memiliki permission tertentu.

        Args:
            telegram_id: Telegram User ID.
            permission: Permission string, misal "docker:write".

        Returns:
            True jika user memiliki permission.
        """
        user = await self.get_user(telegram_id)
        if not user or not user.is_active or user.is_blocked:
            return False
        role_perms = ROLE_PERMISSIONS.get(user.role, frozenset())
        return permission in role_perms

    async def add_user(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str,
        role: str,
        added_by: int,
    ) -> UserDTO:
        """Tambah pengguna baru ke whitelist.

        Args:
            telegram_id: Telegram User ID pengguna baru.
            username: Username Telegram.
            full_name: Nama lengkap.
            role: Role RBAC.
            added_by: Telegram ID admin yang menambahkan.

        Returns:
            UserDTO pengguna yang baru ditambahkan.

        Raises:
            UserAlreadyExistsError: Jika user sudah terdaftar.
            InvalidRoleError: Jika role tidak valid.
        """
        if role not in VALID_ROLES:
            raise InvalidRoleError(f"Role '{role}' tidak valid. Pilihan: {sorted(VALID_ROLES)}")

        existing = await self._find_user_by_telegram_id(telegram_id)
        if existing:
            raise UserAlreadyExistsError(
                f"User dengan Telegram ID {telegram_id} sudah terdaftar."
            )

        adder_row = await self._db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?", (added_by,)
        )
        adder_id = adder_row["id"] if adder_row else None

        cursor = await self._db.execute(
            """INSERT INTO users (telegram_id, username, full_name, role, added_by)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_id, username, full_name, role, adder_id),
        )

        await self._event_bus.publish(
            AuthEvents.USER_ADDED,
            {"telegram_id": telegram_id, "role": role, "added_by": added_by},
        )

        new_user = await self._find_user_by_telegram_id(telegram_id)
        if not new_user:
            raise UserNotFoundError("Gagal mengambil user yang baru dibuat.")

        logger.info(
            "User baru ditambahkan.",
            telegram_id=telegram_id,
            role=role,
            added_by=added_by,
            row_id=cursor.lastrowid,
        )
        return new_user

    async def update_user_role(
        self, telegram_id: int, new_role: str, updated_by: int
    ) -> UserDTO:
        """Ubah role pengguna.

        Args:
            telegram_id: Telegram ID pengguna yang diubah.
            new_role: Role baru.
            updated_by: Telegram ID admin yang mengubah.

        Returns:
            UserDTO dengan role yang sudah diperbarui.

        Raises:
            UserNotFoundError: Jika user tidak ditemukan.
            InvalidRoleError: Jika role tidak valid.
            PermissionDeniedError: Jika mencoba mengubah super_admin.
        """
        if new_role not in VALID_ROLES:
            raise InvalidRoleError(f"Role '{new_role}' tidak valid.")

        user = await self._find_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFoundError(f"User {telegram_id} tidak ditemukan.")

        if user.role == "super_admin" and updated_by not in self._settings.telegram_admin_user_ids:
            raise PermissionDeniedError("Tidak dapat mengubah role super_admin.")

        await self._db.execute(
            "UPDATE users SET role = ?, updated_at = ? WHERE telegram_id = ?",
            (new_role, datetime.utcnow().isoformat(), telegram_id),
        )

        self._cache.pop(telegram_id, None)

        updated = await self._find_user_by_telegram_id(telegram_id)
        if not updated:
            raise UserNotFoundError("Gagal mengambil user setelah update.")

        await self._event_bus.publish(
            AuthEvents.USER_ROLE_CHANGED,
            {"telegram_id": telegram_id, "old_role": user.role, "new_role": new_role},
        )

        logger.info("Role user diperbarui.", telegram_id=telegram_id, new_role=new_role)
        return updated

    async def deactivate_user(self, telegram_id: int, deactivated_by: int) -> bool:
        """Nonaktifkan akun pengguna.

        Args:
            telegram_id: Telegram ID pengguna.
            deactivated_by: Telegram ID admin.

        Returns:
            True jika berhasil.

        Raises:
            UserNotFoundError: Jika user tidak ditemukan.
            PermissionDeniedError: Jika mencoba menonaktifkan super_admin.
        """
        user = await self._find_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFoundError(f"User {telegram_id} tidak ditemukan.")

        if user.role == "super_admin":
            raise PermissionDeniedError("Tidak dapat menonaktifkan super_admin.")

        await self._db.execute(
            "UPDATE users SET is_active = 0, updated_at = ? WHERE telegram_id = ?",
            (datetime.utcnow().isoformat(), telegram_id),
        )
        self._cache.pop(telegram_id, None)
        logger.info("User dinonaktifkan.", telegram_id=telegram_id, by=deactivated_by)
        return True

    async def block_user(self, telegram_id: int, blocked_by: int) -> bool:
        """Blokir pengguna.

        Args:
            telegram_id: Telegram ID pengguna.
            blocked_by: Telegram ID admin.

        Returns:
            True jika berhasil.

        Raises:
            UserNotFoundError: Jika user tidak ditemukan.
            PermissionDeniedError: Jika mencoba memblokir super_admin.
        """
        user = await self._find_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFoundError(f"User {telegram_id} tidak ditemukan.")

        if user.role == "super_admin":
            raise PermissionDeniedError("Tidak dapat memblokir super_admin.")

        await self._db.execute(
            "UPDATE users SET is_blocked = 1, updated_at = ? WHERE telegram_id = ?",
            (datetime.utcnow().isoformat(), telegram_id),
        )
        self._cache.pop(telegram_id, None)
        logger.info("User diblokir.", telegram_id=telegram_id, by=blocked_by)
        return True

    async def get_all_alert_recipient_ids(self) -> list[int]:
        """Dapatkan semua Telegram ID yang menerima alert.

        Returns:
            List Telegram ID.
        """
        rows = await self._db.fetch_all(
            """SELECT telegram_id FROM users
               WHERE is_active = 1 AND is_blocked = 0 AND alert_enabled = 1
               AND role IN ('super_admin', 'admin', 'operator')"""
        )
        return [row["telegram_id"] for row in rows]

    async def get_all_users(self) -> list[UserDTO]:
        """Dapatkan semua user yang terdaftar.

        Returns:
            List UserDTO semua user.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM users ORDER BY role, created_at"
        )
        return [self._row_to_dto(row) for row in rows]

    async def _find_user_by_telegram_id(self, telegram_id: int) -> UserDTO | None:
        """Cari user berdasarkan Telegram ID dari database."""
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        if row is None:
            return None
        return self._row_to_dto(row)

    async def _update_user_activity(
        self, telegram_id: int, username: str | None, full_name: str
    ) -> None:
        """Perbarui data aktivitas pengguna."""
        await self._db.execute(
            """UPDATE users SET username = ?, full_name = ?, updated_at = ?
               WHERE telegram_id = ?""",
            (username, full_name, datetime.utcnow().isoformat(), telegram_id),
        )

    @staticmethod
    def _row_to_dto(row: object) -> UserDTO:
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

    def invalidate_cache(self, telegram_id: int | None = None) -> None:
        """Invalidate cache user. Jika telegram_id None, hapus semua cache.

        Args:
            telegram_id: Telegram ID spesifik, atau None untuk semua.
        """
        if telegram_id is None:
            self._cache.clear()
        else:
            self._cache.pop(telegram_id, None)
