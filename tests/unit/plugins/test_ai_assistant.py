"""Unit test untuk ai_assistant plugin dengan Hermes Memory System."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from guardian.plugins.ai_assistant.models import AIMemoryDTO
from guardian.plugins.ai_assistant.service import AIAssistantService


@pytest.fixture
def mock_app_ctx():
    ctx = MagicMock()
    ctx.db = AsyncMock()
    ctx.db.fetch_all.return_value = []
    ctx.db.execute.return_value = MagicMock(lastrowid=1, rowcount=1)
    ctx.settings.ai_provider = "gemini"
    ctx.settings.ai_api_key = "test_key"
    ctx.settings.ai_base_url = "https://one.apprentice.cyou/v1"
    ctx.settings.ai_model = "gemini-2.5-flash"
    ctx.settings.docker_enabled = True
    ctx.settings.cpu_usage_limit = 80.0
    ctx.settings.blocked_packages = ["opencode"]
    return ctx


@pytest.mark.asyncio
async def test_build_system_context_prompt_with_memory(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    prompt = await service.build_system_context_prompt(telegram_id=7896674035)
    assert "Serverinka AI" in prompt
    assert "MEMORI JANGKA PANJANG" in prompt


@pytest.mark.asyncio
async def test_auto_detect_memory(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    await service._auto_detect_and_save_memory(
        telegram_id=7896674035,
        prompt="Mulai sekarang gunakan bahasa santai dan panggilan Bos",
    )
    mock_app_ctx.db.execute.assert_called()


def test_format_markdown_to_telegram_html(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    md_text = "Halo **Bos**, `test code` dan ```python\nprint(123)\n```"
    formatted = service._format_markdown_to_telegram_html(md_text)
    assert "<b>Bos</b>" in formatted
    assert "<code>test code</code>" in formatted
    assert "<pre><code>" in formatted
