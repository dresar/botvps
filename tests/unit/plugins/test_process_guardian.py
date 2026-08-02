"""Unit test untuk process_guardian plugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from guardian.plugins.process_guardian.models import ProcessInfoDTO
from guardian.plugins.process_guardian.service import ProcessGuardianService


@pytest.fixture
def mock_app_ctx():
    ctx = MagicMock()
    ctx.db = AsyncMock()
    ctx.db.fetch_all.return_value = []
    ctx.db.fetch_one.return_value = {"cnt": 0}
    ctx.settings.cpu_usage_limit = 80.0
    ctx.settings.cpu_check_interval = 10
    ctx.settings.cpu_grace_timeout = 1
    ctx.settings.cpu_kill_mode = "auto"
    ctx.settings.cpu_notification = False
    ctx.settings.cpu_cooldown = 10
    ctx.settings.cpu_ignore_users = []
    ctx.settings.cpu_ignore_process = []
    ctx.settings.cpu_ignore_pid = []
    ctx.settings.cpu_ignore_regex = ""
    ctx.audit_service = AsyncMock()
    ctx.auth = AsyncMock()
    ctx.auth.get_all_alert_recipient_ids.return_value = [7896674035]
    ctx.bot_gateway = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_top_cpu_processes_fetching(mock_app_ctx):
    service = ProcessGuardianService(mock_app_ctx)
    procs = await service.get_top_cpu_processes(limit=5)
    assert isinstance(procs, list)


@pytest.mark.asyncio
async def test_is_whitelisted_system_processes(mock_app_ctx):
    service = ProcessGuardianService(mock_app_ctx)
    proc_systemd = ProcessInfoDTO(
        pid=1,
        name="systemd",
        username="root",
        cpu_percent=95.0,
        memory_percent=1.0,
        cmdline="/sbin/init",
        running_time="1d",
        create_time=0.0,
    )
    is_safe = service._is_whitelisted(proc_systemd, db_whitelist=set(), db_blacklist=set())
    assert is_safe is True


@pytest.mark.asyncio
async def test_is_whitelisted_bot_self(mock_app_ctx):
    service = ProcessGuardianService(mock_app_ctx)
    proc_bot = ProcessInfoDTO(
        pid=1234,
        name="python3",
        username="serverinka",
        cpu_percent=99.0,
        memory_percent=5.0,
        cmdline="python -m guardian",
        running_time="10m",
        create_time=0.0,
    )
    is_safe = service._is_whitelisted(proc_bot, db_whitelist=set(), db_blacklist=set())
    assert is_safe is True


@pytest.mark.asyncio
async def test_kill_process_by_pid_not_found(mock_app_ctx):
    service = ProcessGuardianService(mock_app_ctx)
    success, msg = await service.kill_process_by_pid(999999, admin_id=7896674035)
    assert success is False
    assert "tidak ditemukan" in msg
