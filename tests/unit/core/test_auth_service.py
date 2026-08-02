"""Unit tests untuk AuthService."""

import pytest


class TestAuthService:
    """Test suite untuk AuthService."""

    @pytest.mark.asyncio
    async def test_super_admin_bootstrap(self, auth_service, mock_settings):
        """Super admin dari env var harus ada setelah bootstrap."""
        user = await auth_service.get_user(123456789)
        assert user is not None
        assert user.role == "super_admin"
        assert user.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_authenticate_unregistered_user(self, auth_service):
        """User tidak terdaftar harus mendapat hasil tidak terotorisasi."""
        result = await auth_service.authenticate(
            telegram_id=999999, username=None, full_name="Unknown"
        )
        assert result.is_authorized is False
        assert result.user is None
        assert result.denial_reason is not None

    @pytest.mark.asyncio
    async def test_authenticate_super_admin(self, auth_service):
        """Super admin harus berhasil autentikasi."""
        result = await auth_service.authenticate(
            telegram_id=123456789, username="admin", full_name="Test Admin"
        )
        assert result.is_authorized is True
        assert result.user is not None
        assert result.user.role == "super_admin"

    @pytest.mark.asyncio
    async def test_add_user_success(self, auth_service):
        """Menambah user baru harus berhasil."""
        new_user = await auth_service.add_user(
            telegram_id=111111,
            username="newuser",
            full_name="New User",
            role="viewer",
            added_by=123456789,
        )
        assert new_user.telegram_id == 111111
        assert new_user.role == "viewer"

    @pytest.mark.asyncio
    async def test_add_user_duplicate_fails(self, auth_service):
        """Menambah user yang sudah ada harus gagal."""
        from guardian.core.exceptions import UserAlreadyExistsError

        await auth_service.add_user(
            telegram_id=222222, username=None, full_name="User A",
            role="viewer", added_by=123456789,
        )
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.add_user(
                telegram_id=222222, username=None, full_name="User A Duplicate",
                role="operator", added_by=123456789,
            )

    @pytest.mark.asyncio
    async def test_has_permission_viewer(self, auth_service):
        """Viewer tidak boleh punya permission write."""
        await auth_service.add_user(
            telegram_id=333333, username=None, full_name="Viewer User",
            role="viewer", added_by=123456789,
        )
        has_read = await auth_service.has_permission(333333, "system:read")
        has_write = await auth_service.has_permission(333333, "system:write")
        assert has_read is True
        assert has_write is False

    @pytest.mark.asyncio
    async def test_has_permission_super_admin(self, auth_service):
        """Super admin harus punya semua permission."""
        has_all = await auth_service.has_permission(123456789, "bot:admin")
        assert has_all is True

    @pytest.mark.asyncio
    async def test_update_role(self, auth_service):
        """Update role harus mengubah role user."""
        await auth_service.add_user(
            telegram_id=444444, username=None, full_name="Operator User",
            role="operator", added_by=123456789,
        )
        updated = await auth_service.update_user_role(
            telegram_id=444444, new_role="admin", updated_by=123456789
        )
        assert updated.role == "admin"

    @pytest.mark.asyncio
    async def test_invalid_role_raises(self, auth_service):
        """Role yang tidak valid harus raise InvalidRoleError."""
        from guardian.core.exceptions import InvalidRoleError

        with pytest.raises(InvalidRoleError):
            await auth_service.add_user(
                telegram_id=555555, username=None, full_name="Bad Role",
                role="hacker", added_by=123456789,
            )

    @pytest.mark.asyncio
    async def test_deactivate_user(self, auth_service):
        """Menonaktifkan user harus membuatnya tidak dapat autentikasi."""
        await auth_service.add_user(
            telegram_id=666666, username=None, full_name="To Deactivate",
            role="viewer", added_by=123456789,
        )
        await auth_service.deactivate_user(telegram_id=666666, deactivated_by=123456789)

        result = await auth_service.authenticate(
            telegram_id=666666, username=None, full_name="To Deactivate"
        )
        assert result.is_authorized is False
