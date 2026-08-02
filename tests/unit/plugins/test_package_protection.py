"""Unit test untuk package_protection plugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from guardian.plugins.package_protection.service import PackageProtectionService


@pytest.fixture
def mock_app_ctx():
    ctx = MagicMock()
    ctx.database = AsyncMock()
    ctx.db = ctx.database
    ctx.database.fetch_all.return_value = [{"name": "opencode"}]
    ctx.settings.package_guard_enabled = True
    ctx.settings.package_scan_interval_minutes = 10
    ctx.audit_service = AsyncMock()
    ctx.auth = AsyncMock()
    ctx.auth.get_all_alert_recipient_ids.return_value = [7896674035]
    ctx.bot_gateway = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_package_protection_full_scan_clean(mock_app_ctx):
    service = PackageProtectionService(mock_app_ctx)
    reports = await service.run_full_scan()
    assert isinstance(reports, list)


@pytest.mark.asyncio
async def test_uninstall_package_manual_clean(mock_app_ctx):
    service = PackageProtectionService(mock_app_ctx)
    success, msg = await service.uninstall_package_manual("non_existent_package_123")
    assert success is False
    assert "Tidak ditemukan" in msg
