"""AIService — Official Google AI Studio Gemini API & Groq Backup Integration untuk Serverinka Guardian."""

import base64
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError

if TYPE_CHECKING:
    from guardian.core.config import GuardianSettings

logger = structlog.get_logger(__name__)


class AIService:
    """Service untuk interaksi dengan Google Gemini 2.5 Flash & Groq AI (Llama 3.3 70B & Vision).

    Menggunakan httpx.AsyncClient untuk komunikasi async non-blocking.
    Mendukung rotasi API Key dari SQLite Key Pool & Multimodal Vision.

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
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        media_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> str:
        """Kirim permintaan Chat Completion ke Google AI Studio atau Groq AI API.

        Args:
            messages: List dict berisi pesan [{"role": "user", "content": "..."}].
            system_prompt: System prompt opsional.
            api_key: API Key spesifik (misal dari SQLite Key Pool).
            provider: Provider AI ('gemini', 'groq', 'openai').
            model: Model AI yang ingin digunakan.
            temperature: Parameter kreativitas response.
            media_bytes: Bytes file gambar, foto, atau dokumen.
            mime_type: MIME type media (misal: 'image/jpeg', 'application/pdf', 'text/plain').

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
                "Belum ada API Key yang tersedia di SQLite Key Pool!"
            )

        target_provider = (provider or self._settings.ai_provider).lower()
        target_model = model or (
            "llama-3.3-70b-versatile" if target_provider == "groq" else self._settings.ai_model
        )

        if target_provider == "gemini":
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={target_key}"

            contents = []
            for i, msg in enumerate(messages):
                role = "user" if msg.get("role") == "user" else "model"
                parts: list[dict[str, Any]] = [{"text": msg.get("content", "")}]
                if i == len(messages) - 1 and media_bytes:
                    b64_data = base64.b64encode(media_bytes).decode("utf-8")
                    parts.append({
                        "inlineData": {
                            "mime_type": mime_type or "image/jpeg",
                            "data": b64_data,
                        }
                    })
                contents.append({"role": role, "parts": parts})

            body: dict[str, Any] = {
                "contents": contents,
                "generationConfig": {"temperature": temperature},
            }
            if system_prompt:
                body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

            logger.debug("Mengirim request ke Official Google Gemini API...", model=target_model)

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
                raise AIProviderError(
                    f"Google Gemini API Error (Status {e.response.status_code})",
                    detail=e.response.text,
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                logger.error("Network Error saat menghubungi Google Gemini API", error=str(e))
                raise AIProviderError(
                    f"Gagal menghubungi Google Gemini API: {e}",
                    detail=str(e),
                ) from e
            except Exception as e:
                logger.exception("Error tak terduga pada AIService Gemini.")
                raise AIProviderError(f"Error AI Completion Gemini: {e}") from e

        elif target_provider == "groq":
            endpoint = "https://api.groq.com/openai/v1/chat/completions"

            full_messages = []
            if media_bytes:
                # Otomatis gunakan Groq Vision Model jika terdapat media gambar/foto
                target_model = "llama-3.2-11b-vision-preview"
                b64_data = base64.b64encode(media_bytes).decode("utf-8")
                data_url = f"data:{mime_type or 'image/jpeg'};base64,{b64_data}"

                vision_messages = []
                for msg in messages[:-1]:
                    vision_messages.append(msg)

                last_user_prompt = messages[-1].get("content", "") if messages else ""
                vision_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": last_user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                })
                if system_prompt:
                    full_messages = [{"role": "system", "content": system_prompt}] + vision_messages
                else:
                    full_messages = vision_messages
            else:
                if system_prompt:
                    full_messages.append({"role": "system", "content": system_prompt})
                full_messages.extend(messages)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {target_key}",
            }
            body = {
                "model": target_model,
                "messages": full_messages,
                "temperature": temperature,
            }

            logger.debug("Mengirim request ke Groq AI API...", model=target_model)

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(endpoint, headers=headers, json=body)
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"HTTP Status {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                    raise AIProviderError("Response Groq AI tidak berisi pilihan balasan valid.")

            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP Error dari Groq AI API",
                    status_code=e.response.status_code,
                    body=e.response.text,
                )
                raise AIProviderError(
                    f"Groq AI API Error (Status {e.response.status_code})",
                    detail=e.response.text,
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                logger.error("Network Error saat menghubungi Groq AI API", error=str(e))
                raise AIProviderError(
                    f"Gagal menghubungi Groq AI API: {e}",
                    detail=str(e),
                ) from e
            except Exception as e:
                logger.exception("Error tak terduga pada AIService Groq.")
                raise AIProviderError(f"Error AI Completion Groq: {e}") from e

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
                "model": target_model,
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
                raise AIProviderError(f"Error AI Provider {target_provider}: {e}") from e
