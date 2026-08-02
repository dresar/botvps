"""Unit test untuk AIService."""

from unittest.mock import MagicMock, patch
import pytest

from guardian.core.ai_service import AIService
from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError


@pytest.mark.asyncio
async def test_ai_service_disabled(mock_settings):
    """AIService harus raise AIProviderNotConfiguredError jika disabled."""
    mock_settings.ai_provider = "disabled"
    service = AIService(mock_settings)

    assert service.is_enabled is False
    with pytest.raises(AIProviderNotConfiguredError):
        await service.chat_completion([{"role": "user", "content": "Halo"}])


@pytest.mark.asyncio
async def test_ai_service_gemini_success(mock_settings):
    """AIService harus berhasil memproses respon Google AI Studio Gemini 2.5 Flash format."""
    mock_settings.ai_provider = "gemini"
    mock_settings.ai_api_key = "test_key"
    mock_settings.ai_model = "gemini-2.5-flash"

    service = AIService(mock_settings)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "Halo! Saya adalah asisten AI Serverinka."
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await service.chat_completion([{"role": "user", "content": "Halo"}])
        assert "Serverinka" in result


@pytest.mark.asyncio
async def test_ai_service_openai_success(mock_settings):
    """AIService harus memproses format OpenAI untuk provider non-gemini."""
    mock_settings.ai_provider = "openai"
    mock_settings.ai_api_key = "test_key"
    mock_settings.ai_model = "gpt-4o"

    service = AIService(mock_settings)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Halo! Saya OpenAI.",
                }
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await service.chat_completion([{"role": "user", "content": "Halo"}])
        assert "OpenAI" in result
