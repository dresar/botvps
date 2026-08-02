"""Unit tests untuk validators."""

import pytest

from guardian.utils.validators import (
    is_dangerous_service,
    is_valid_container_name,
    is_valid_cron_expression,
    is_valid_pid,
    is_valid_role,
    is_valid_service_name,
    is_valid_telegram_id,
    sanitize_log_output,
)


class TestServiceNameValidator:
    def test_valid_names(self):
        assert is_valid_service_name("nginx.service")
        assert is_valid_service_name("my-app")
        assert is_valid_service_name("systemd-journald")
        assert is_valid_service_name("app@1.service")

    def test_invalid_empty(self):
        assert not is_valid_service_name("")

    def test_invalid_special_chars(self):
        assert not is_valid_service_name("rm -rf /")
        assert not is_valid_service_name("service; whoami")

    def test_too_long(self):
        assert not is_valid_service_name("a" * 300)


class TestDangerousService:
    def test_dangerous_services(self):
        assert is_dangerous_service("sshd")
        assert is_dangerous_service("systemd")
        assert is_dangerous_service("serverinka-guardian")

    def test_not_dangerous(self):
        assert not is_dangerous_service("nginx")
        assert not is_dangerous_service("my-app")

    def test_with_service_extension(self):
        assert is_dangerous_service("sshd.service")


class TestContainerNameValidator:
    def test_valid_names(self):
        assert is_valid_container_name("my-app")
        assert is_valid_container_name("nginx_prod")
        assert is_valid_container_name("app123")

    def test_invalid_start_char(self):
        assert not is_valid_container_name("-invalid")

    def test_empty(self):
        assert not is_valid_container_name("")


class TestPIDValidator:
    def test_valid_pid(self):
        assert is_valid_pid("1")
        assert is_valid_pid("12345")

    def test_invalid_zero(self):
        assert not is_valid_pid("0")

    def test_invalid_negative(self):
        assert not is_valid_pid("-1")

    def test_invalid_string(self):
        assert not is_valid_pid("abc")


class TestRoleValidator:
    def test_valid_roles(self):
        assert is_valid_role("super_admin")
        assert is_valid_role("admin")
        assert is_valid_role("operator")
        assert is_valid_role("viewer")

    def test_invalid_role(self):
        assert not is_valid_role("hacker")
        assert not is_valid_role("root")


class TestCronExpression:
    def test_valid_expressions(self):
        assert is_valid_cron_expression("* * * * *")
        assert is_valid_cron_expression("0 2 * * *")
        assert is_valid_cron_expression("0 2 1 * 0")

    def test_invalid_expressions(self):
        assert not is_valid_cron_expression("* * *")
        assert not is_valid_cron_expression("not a cron")


class TestSanitizeLog:
    def test_removes_control_chars(self):
        text = "normal\x00text\x01with\x02control"
        result = sanitize_log_output(text)
        assert "\x00" not in result
        assert "\x01" not in result

    def test_preserves_newlines(self):
        text = "line1\nline2\nline3"
        result = sanitize_log_output(text)
        assert "\n" in result

    def test_truncates_long_output(self):
        text = "a" * 5000
        result = sanitize_log_output(text, max_length=100)
        assert len(result) <= 100
