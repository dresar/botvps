"""Unit tests untuk GuardianSettings."""

import os

import pytest
from pydantic import ValidationError


def test_settings_requires_bot_token():
    """Settings harus gagal jika TELEGRAM_BOT_TOKEN tidak ada."""
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("TELEGRAM_ADMIN_USER_IDS", None)

    from guardian.core.config import GuardianSettings
    with pytest.raises((ValidationError, Exception)):
        GuardianSettings(_env_file=None)  # type: ignore[call-arg]


def test_parse_admin_ids_from_string():
    """Admin IDs harus dapat di-parse dari string comma-separated."""
    from guardian.core.config import GuardianSettings

    settings = GuardianSettings(
        telegram_bot_token="test_token:123",
        telegram_admin_user_ids="123,456,789",  # type: ignore[arg-type]
    )
    assert settings.telegram_admin_user_ids == [123, 456, 789]


def test_parse_single_admin_id():
    """Satu admin ID harus dapat di-parse dengan benar."""
    from guardian.core.config import GuardianSettings

    settings = GuardianSettings(
        telegram_bot_token="test_token:123",
        telegram_admin_user_ids="123456789",  # type: ignore[arg-type]
    )
    assert settings.telegram_admin_user_ids == [123456789]


def test_invalid_log_level():
    """Log level yang tidak valid harus menyebabkan ValidationError."""
    from guardian.core.config import GuardianSettings

    with pytest.raises(ValidationError):
        GuardianSettings(
            telegram_bot_token="test:123",
            telegram_admin_user_ids=[123],
            log_level="INVALID",
        )


def test_invalid_telegram_mode():
    """Telegram mode yang tidak valid harus menyebabkan ValidationError."""
    from guardian.core.config import GuardianSettings

    with pytest.raises(ValidationError):
        GuardianSettings(
            telegram_bot_token="test:123",
            telegram_admin_user_ids=[123],
            telegram_mode="ftp",
        )


def test_default_values():
    """Nilai default harus sesuai dengan yang didokumentasikan."""
    from guardian.core.config import GuardianSettings

    settings = GuardianSettings(
        telegram_bot_token="test:123",
        telegram_admin_user_ids=[123],
    )
    assert settings.log_level == "INFO"
    assert settings.telegram_mode == "polling"
    assert settings.scheduler_alert_interval_seconds == 60
    assert settings.rate_limit_commands_per_window == 30
    assert settings.docker_enabled is True


def test_disabled_plugins_empty_string():
    """String kosong untuk DISABLED_PLUGINS harus menghasilkan list kosong."""
    from guardian.core.config import GuardianSettings

    settings = GuardianSettings(
        telegram_bot_token="test:123",
        telegram_admin_user_ids=[123],
        disabled_plugins="",  # type: ignore[arg-type]
    )
    assert settings.disabled_plugins == []


def test_disabled_plugins_comma_separated():
    """DISABLED_PLUGINS comma-separated harus di-parse dengan benar."""
    from guardian.core.config import GuardianSettings

    settings = GuardianSettings(
        telegram_bot_token="test:123",
        telegram_admin_user_ids=[123],
        disabled_plugins="docker,notification",  # type: ignore[arg-type]
    )
    assert settings.disabled_plugins == ["docker", "notification"]
