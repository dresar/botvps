"""AIService — Official Google AI Studio Gemini API Integration untuk Serverinka Guardian."""

from typing import TYPE_CHECKING, Any

import httpx
import structlog

from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError

if TYPE_CHECKING:
    from guardian.core.config import GuardianSettings

logger = structlog.get_logger(__name__)


class AIService:
    """Service untuk interaksi dengan Official Google AI Studio API (Gemini 2.5 Flash).

    Menggunakan httpx.AsyncClient untuk komunikasi async non-blocking.
    Mendukung rotasi API Key dari SQLite Key Pool.

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
        api_key: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Kirim permintaan Chat Completion ke Official Google AI Studio API.

        Args:
            messages: List dict berisi pesan [{"role": "user", "content": "..."}].
            system_prompt: System prompt opsional.
            api_key: API Key spesifik (misal dari SQLite Key Pool).
            temperature: Parameter kreativitas response.

        Returns:
            Teks respon dari AI.

        Raises:
            AIProviderNotConfiguredError: Jika AI provider dinonaktifkan atau API Key kosong.
            AIProviderError: Jika panggilan HTTP ke API gagal.
        """
        if not self.is_enabled:
            raise AIProviderNotConfiguredError("AI Provider dinonaktifkan dalam konfigurasi.")

        target_key = api_key or self._settings.ai_api_key
        if not target_key:
            raise AIProviderNotConfiguredError(
                "Belum ada Gemini API Key yang tersedia di SQLite Key Pool!"
            )

        model = self._settings.ai_model or "gemini-2.5-flash"
        provider = self._settings.ai_provider.lower()

        if provider == "gemini":
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={target_key}"

            contents = []
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

            body: dict[str, Any] = {
                "contents": contents,
                "generationConfig": {"temperature": temperature},
            }
            if system_prompt:
                body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

            logger.debug("Mengirim request ke Official Google Gemini API...", model=model)

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(endpoint, json=body)
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"HTTP Status {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    data = response.json()

                    candidates = data.get("candidates", [])
                    if candidates and len(candidates) > 0:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and len(parts) > 0:
                            content = parts[0].get("text", "").strip()
                            return content
                    raise AIProviderError("Response Google Gemini tidak berisi balasan valid.")

            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP Error dari Google Gemini API",
                    status_code=e.response.status_code,
                    body=e.response.text,
                )
                err_detail = e.response.text
                raise AIProviderError(
                    f"Google Gemini API Error (Status {e.response.status_code})",
                    detail=err_detail,
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                logger.error("Network Error saat menghubungi Google Gemini API", error=str(e))
                raise AIProviderError(
                    f"Gagal menghubungi Google Gemini API: {e}",
                    detail=str(e),
                ) from e
            except Exception as e:
                logger.exception("Error tak terduga pada AIService.")
                raise AIProviderError(f"Error AI Completion: {e}") from e

        else:
            # Fallback untuk OpenAI / Custom Provider Format
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {target_key}",
            }
            body = {
                "model": model,
                "messages": full_messages,
                "temperature": temperature,
            }
            endpoint = "https://api.openai.com/v1/chat/completions"

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(endpoint, headers=headers, json=body)
                    response.raise_for_status()
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                    raise AIProviderError("Response AI tidak valid.")
            except Exception as e:
                raise AIProviderError(f"Error AI Provider {provider}: {e}") from e
