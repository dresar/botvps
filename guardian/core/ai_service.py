"""AIService — Gateway AI integration untuk Serverinka Guardian."""

from typing import TYPE_CHECKING, Any

import httpx
import structlog

from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError

if TYPE_CHECKING:
    from guardian.core.config import GuardianSettings

logger = structlog.get_logger(__name__)


class AIService:
    """Service untuk interaksi dengan AI Chat Completions Gateway API.

    Menggunakan httpx.AsyncClient untuk komunikasi async non-blocking.
    Mendukung format OpenAI standard (`/v1/chat/completions`).

    Args:
        settings: GuardianSettings instance.
    """

    def __init__(self, settings: "GuardianSettings") -> None:
        self._settings = settings

    @property
    def is_enabled(self) -> bool:
        """True jika AI provider aktif (bukan 'disabled')."""
        return self._settings.ai_provider != "disabled"

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Kirim permintaan Chat Completion ke AI Gateway.

        Args:
            messages: List dict berisi pesan [{"role": "user", "content": "..."}].
            system_prompt: System prompt opsional.
            temperature: Parameter kreativitas response.

        Returns:
            Teks respon dari AI.

        Raises:
            AIProviderNotConfiguredError: Jika AI provider dinonaktifkan atau API Key kosong.
            AIProviderError: Jika panggilan HTTP ke AI Gateway gagal.
        """
        if not self.is_enabled:
            raise AIProviderNotConfiguredError("AI Provider dinonaktifkan dalam konfigurasi.")

        if not self._settings.ai_api_key:
            raise AIProviderNotConfiguredError("AI API Key belum dikonfigurasi.")

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._settings.ai_api_key}",
        }

        body = {
            "model": self._settings.ai_model,
            "messages": full_messages,
            "temperature": temperature,
        }

        endpoint = f"{self._settings.ai_base_url.rstrip('/')}/chat/completions"

        logger.debug("Mengirim request ke AI Gateway...", endpoint=endpoint, model=self._settings.ai_model)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()

                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    return content
                raise AIProviderError("Response AI tidak berisi pilihan balasan valid.")

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error dari AI Gateway.", status_code=e.response.status_code, body=e.response.text)
            raise AIProviderError(
                f"AI Gateway mengembalikan HTTP status {e.response.status_code}.",
                detail=e.response.text,
            ) from e
        except httpx.RequestError as e:
            logger.error("Network error saat mengakses AI Gateway.", error=str(e))
            raise AIProviderError(
                f"Gagal menghubung AI Gateway: {e}",
                detail=str(e),
            ) from e
        except Exception as e:
            logger.exception("Error tak terduga pada AIService.")
            raise AIProviderError(f"Error AI Completion: {e}") from e
