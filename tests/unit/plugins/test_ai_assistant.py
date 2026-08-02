"""Unit test untuk ai_assistant plugin & AIAssistantService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from guardian.plugins.ai_assistant.service import AIAssistantService


@pytest.fixture
def mock_app_ctx():
    ctx = MagicMock()
    ctx.settings.ai_provider = "gemini"
    ctx.settings.ai_api_key = "test_key"
    ctx.settings.ai_base_url = "https://one.apprentice.cyou/v1"
    ctx.settings.ai_model = "gemini-2.5-flash"
    ctx.settings.docker_enabled = True
    ctx.settings.cpu_usage_limit = 80.0
    ctx.settings.blocked_packages = ["opencode"]
    return ctx


@pytest.mark.asyncio
async def test_build_system_context_prompt(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    prompt = await service.build_system_context_prompt()
    assert "Serverinka AI" in prompt
    assert "CPU Usage" in prompt
    assert "RAM Usage" in prompt


def test_format_markdown_to_telegram_html(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    md_text = "Halo **dunia**, `test code` dan ```python\nprint(123)\n```"
    formatted = service._format_markdown_to_telegram_html(md_text)
    assert "<b>dunia</b>" in formatted
    assert "<code>test code</code>" in formatted
    assert "<pre><code>" in formatted
