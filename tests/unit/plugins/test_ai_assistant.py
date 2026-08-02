"""Unit test untuk ai_assistant plugin dengan Hermes Memory System, Gemini & Groq Key Pool, serta Skill Engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from guardian.plugins.ai_assistant.models import AIMemoryDTO
from guardian.plugins.ai_assistant.service import AIAssistantService


@pytest.fixture
def mock_app_ctx():
    ctx = MagicMock()
    ctx.database = AsyncMock()
    ctx.db = ctx.database
    ctx.database.fetch_all.return_value = []
    ctx.database.fetch_one.return_value = {"api_key": "AIzaSyKeyTest", "cnt": 5, "total_use": 100}
    ctx.database.execute.return_value = MagicMock(lastrowid=1, rowcount=1)
    ctx.settings.ai_provider = "gemini"
    ctx.settings.ai_api_key = "test_key"
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
    mock_app_ctx.database.execute.assert_called()


def test_format_markdown_to_telegram_html(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    md_text = "Halo **Bos**, `test code` dan ```python\nprint(123)\n```"
    formatted = service._format_markdown_to_telegram_html(md_text)
    assert "<b>Bos</b>" in formatted
    assert "<code>test code</code>" in formatted
    assert "<pre><code>" in formatted


@pytest.mark.asyncio
async def test_add_api_keys(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    added, dupes = await service.repo.add_api_keys(["AIzaSyKey1", "AIzaSyKey2", "AIzaSyKey3"])
    assert added == 3
    assert dupes == 0


@pytest.mark.asyncio
async def test_add_groq_keys(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    added, dupes = await service.repo.add_groq_keys(["gsk_key1", "gsk_key2"])
    assert added == 2
    assert dupes == 0


@pytest.mark.asyncio
async def test_add_and_get_skills(mock_app_ctx):
    service = AIAssistantService(mock_app_ctx)
    sk = await service.repo.add_skill(
        skill_name="Penghemat RAM",
        description="Analisis RAM VPS",
        instructions="Selalu rekomendasikan 3 langkah hemat RAM",
    )
    assert sk["id"] == 1
    assert sk["skill_name"] == "Penghemat RAM"
