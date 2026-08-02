"""Unit tests untuk utility formatters."""

import pytest

from guardian.utils.formatters import (
    escape_html,
    format_bytes,
    format_load_average,
    format_uptime,
    make_progress_bar,
    truncate_text,
)


class TestFormatBytes:
    def test_zero_bytes(self):
        assert format_bytes(0) == "0 B"

    def test_bytes(self):
        assert format_bytes(512) == "512.0 B"

    def test_kilobytes(self):
        assert format_bytes(1024) == "1.0 KB"

    def test_megabytes(self):
        assert format_bytes(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"

    def test_negative_bytes(self):
        assert format_bytes(-100) == "0 B"


class TestFormatUptime:
    def test_seconds_only(self):
        assert "45 detik" in format_uptime(45)

    def test_minutes(self):
        assert "menit" in format_uptime(3600)

    def test_hours(self):
        assert "jam" in format_uptime(7200)

    def test_days(self):
        assert "hari" in format_uptime(86400)

    def test_zero(self):
        assert "detik" in format_uptime(0)


class TestMakeProgressBar:
    def test_zero_percent(self):
        bar = make_progress_bar(0, width=10)
        assert bar == "░" * 10

    def test_hundred_percent(self):
        bar = make_progress_bar(100, width=10)
        assert bar == "█" * 10

    def test_fifty_percent(self):
        bar = make_progress_bar(50, width=10)
        assert bar.count("█") == 5
        assert bar.count("░") == 5

    def test_width_respected(self):
        bar = make_progress_bar(50, width=8)
        assert len(bar) == 8

    def test_clamped_below_zero(self):
        bar = make_progress_bar(-10)
        assert "█" not in bar

    def test_clamped_above_hundred(self):
        bar = make_progress_bar(150)
        assert "░" not in bar


class TestEscapeHtml:
    def test_ampersand(self):
        assert escape_html("AT&T") == "AT&amp;T"

    def test_less_than(self):
        assert escape_html("<script>") == "&lt;script&gt;"

    def test_no_special_chars(self):
        assert escape_html("normal text") == "normal text"


class TestTruncateText:
    def test_short_text_unchanged(self):
        text = "Hello"
        assert truncate_text(text, max_length=100) == "Hello"

    def test_long_text_truncated(self):
        text = "a" * 200
        result = truncate_text(text, max_length=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_exact_length(self):
        text = "a" * 100
        result = truncate_text(text, max_length=100)
        assert result == text
