"""Fixtures pytest untuk testing Serverinka Guardian."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio




@pytest_asyncio.fixture
async def in_memory_db():
    """DatabaseManager dengan SQLite in-memory untuk testing."""
    from guardian.core.database import DatabaseManager

    db = DatabaseManager(":memory:")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def mock_settings():
    """Mock GuardianSettings untuk testing."""
    settings = MagicMock()
    settings.telegram_bot_token = "test_token"
    settings.telegram_admin_user_ids = [123456789]
    settings.database_path = ":memory:"
    settings.log_level = "DEBUG"
    settings.rate_limit_commands_per_window = 30
    settings.rate_limit_window_seconds = 60
    settings.scheduler_alert_interval_seconds = 60
    settings.docker_enabled = False
    settings.disabled_plugins = []
    settings.ai_provider = "disabled"
    return settings


@pytest.fixture
def mock_event_bus():
    """Mock EventBus untuk testing."""
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.subscribe = MagicMock()
    return bus


@pytest_asyncio.fixture
async def auth_service(in_memory_db, mock_settings, mock_event_bus):
    """AuthService yang terkoneksi ke database in-memory."""
    from guardian.core.auth_service import AuthService

    auth = AuthService(
        db=in_memory_db,
        event_bus=mock_event_bus,
        settings=mock_settings,
    )
    await auth.bootstrap_super_admins()
    return auth


@pytest.fixture
def mock_bot_gateway():
    """Mock BotGateway untuk testing handlers."""
    gateway = MagicMock()
    gateway.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    gateway.edit_message = AsyncMock(return_value=MagicMock(message_id=1))
    gateway.answer_callback_query = AsyncMock()
    return gateway


@pytest_asyncio.fixture
async def app_ctx(in_memory_db, mock_settings, mock_event_bus, mock_bot_gateway):
    """ApplicationContext lengkap untuk integration testing."""
    from guardian.core.auth_service import AuthService
    from guardian.core.engine import ApplicationContext
    from guardian.core.plugin_manager import PluginManager
    from guardian.core.scheduler import SchedulerEngine

    auth = AuthService(in_memory_db, mock_event_bus, mock_settings)
    await auth.bootstrap_super_admins()

    scheduler = MagicMock()
    scheduler.add_interval_job = MagicMock()
    scheduler.get_jobs = MagicMock(return_value=[])

    pm = PluginManager()

    ctx = ApplicationContext(
        settings=mock_settings,
        database=in_memory_db,
        event_bus=mock_event_bus,
        scheduler=scheduler,
        auth=auth,
        plugin_manager=pm,
        bot=mock_bot_gateway,
    )

    return ctx
