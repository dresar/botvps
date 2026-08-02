"""Service cerdas untuk AI Assistant dengan Hermes Long-Term & Short-Term Memory System dan SQLite Gemini Key Pool."""

import asyncio
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import psutil
import structlog

from guardian.core.ai_service import AIService
from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.ai_assistant.repository import AIMemoryRepository
from guardian.utils.formatters import escape_html, format_bytes, format_uptime

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class AIAssistantService(BaseService):
    """Service AI Assistant cerdas berbasis Hermes Memory System & SQLite Key Pool."""

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self.ai_client = AIService(ctx.settings)
        self.repo = AIMemoryRepository(ctx.database)

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan AI Service."""
        status = "healthy" if self.ai_client.is_enabled else "degraded"
        return ServiceHealth(
            service_name="AIAssistantService",
            status=status,
            message="AI Assistant Hermes Memory & Key Pool Siap." if status == "healthy" else "AI Assistant Disabled.",
            checked_at=datetime.utcnow(),
        )

    async def build_system_context_prompt(self, telegram_id: int) -> str:
        """Kumpulkan statistik VPS real-time dan Long-Term Memory / Aturan Pengguna."""
        def _get_metrics() -> dict[str, Any]:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            uptime_sec = int(time.time() - psutil.boot_time())
            return {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "cpu_count": psutil.cpu_count(logical=True),
                "ram_used": format_bytes(mem.used),
                "ram_total": format_bytes(mem.total),
                "ram_percent": mem.percent,
                "disk_used": format_bytes(disk.used),
                "disk_total": format_bytes(disk.total),
                "disk_percent": disk.percent,
                "uptime": format_uptime(uptime_sec),
            }

        m = await asyncio.to_thread(_get_metrics)

        memories = await self.repo.get_memories(telegram_id)
        memory_lines = []
        if memories:
            for mem in memories:
                memory_lines.append(f"- [{mem.memory_type.upper()}] {mem.content}")
        memory_str = "\n".join(memory_lines) if memory_lines else "Belum ada memori khusus tersimpan."

        docker_info = "Aktif" if self._ctx.settings.docker_enabled else "Non-Aktif"
        cpu_guard_info = f"Aktif (Batas {self._ctx.settings.cpu_usage_limit}%)"

        system_prompt = (
            f"Anda adalah 'Serverinka AI', asisten AI pintar pengelola VPS berbasis Google Gemini 2.5 Flash.\n\n"
            f"🧠 MEMORI JANGKA PANJANG & ATURAN PENGGUNA (HERMES MEMORY SYSTEM):\n"
            f"{memory_str}\n\n"
            f"📊 METRIK & STATUS VPS REAL-TIME SAAT INI:\n"
            f"• CPU Usage: {m['cpu_percent']}% ({m['cpu_count']} Cores)\n"
            f"• RAM Usage: {m['ram_used']} / {m['ram_total']} ({m['ram_percent']}%)\n"
            f"• Disk Usage: {m['disk_used']} / {m['disk_total']} ({m['disk_percent']}%)\n"
            f"• Uptime VPS: {m['uptime']}\n"
            f"• Docker Integration: {docker_info}\n"
            f"• CPU Guard: {cpu_guard_info}\n\n"
            f"PEDOMAN RESPON:\n"
            f"1. PATUHI SELURUH ATURAN DAN MEMORI JANGKA PANJANG PENGGUNA DI ATAS. Jika memori meminta bahasa santai/gaul/non-formal, gunakan gaya bahasa tersebut secara konsisten!\n"
            f"2. Gunakan status VPS real-time untuk menjawab pertanyaan teknis.\n"
            f"3. Berikan balasan yang jelas, solutif, dan ramah."
        )
        return system_prompt

    async def ask_ai(self, telegram_id: int, user_prompt: str) -> str:
        """Kirim pertanyaan pengguna ke AI dengan memori & konteks histori percakapan."""
        # 1. Otomatis deteksi jika user memberikan instruksi/memori baru
        await self._auto_detect_and_save_memory(telegram_id, user_prompt)

        # 2. Ambil histori percakapan (Short-Term Memory)
        history = await self.repo.get_recent_chat_history(telegram_id, limit=8)
        messages = [{"role": h.role, "content": h.content} for h in history]
        messages.append({"role": "user", "content": user_prompt})

        # 3. Buat System Prompt dengan statistik VPS & Memori Jangka Panjang
        system_prompt = await self.build_system_context_prompt(telegram_id)

        # 4. Panggil AI Client dengan Key Rotation & Failover dari SQLite Key Pool
        raw_response = await self._call_ai_with_key_rotation(messages, system_prompt)

        # 5. Simpan percakapan ke Short-Term Memory
        await self.repo.add_chat_turn(telegram_id, "user", user_prompt)
        await self.repo.add_chat_turn(telegram_id, "assistant", raw_response)

        return self._format_markdown_to_telegram_html(raw_response)

    async def _call_ai_with_key_rotation(
        self, messages: list[dict[str, str]], system_prompt: str
    ) -> str:
        """Kirim pesan ke AI dengan Key Rotation & Auto-Failover dari SQLite Key Pool."""
        max_attempts = 5
        last_exception: Exception | None = None

        for attempt in range(max_attempts):
            api_key = await self.repo.get_next_active_key()
            if not api_key:
                # Fallback ke config jika tidak ada key di SQLite pool
                api_key = self._ctx.settings.ai_api_key or None

            if not api_key:
                raise AIProviderNotConfiguredError(
                    "Belum ada Gemini API Key yang aktif di SQLite Key Pool!\n\n"
                    "Gunakan perintah Telegram berikut untuk menambahkan API Key:\n"
                    "<code>/ai addkey AIzaSyKey1 AIzaSyKey2 ...</code>"
                )

            try:
                raw_response = await self.ai_client.chat_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    api_key=api_key,
                    temperature=0.7,
                )
                if api_key != self._ctx.settings.ai_api_key:
                    await self.repo.record_key_success(api_key)
                return raw_response

            except AIProviderError as e:
                last_exception = e
                logger.warning(
                    "Gemini API Key mengalami kendala, mencoba key berikutnya...",
                    attempt=attempt + 1,
                    api_key_prefix=api_key[:10] if api_key else "empty",
                    error=str(e),
                )
                if api_key and api_key != self._ctx.settings.ai_api_key:
                    await self.repo.record_key_error(
                        api_key, str(e), getattr(e, "status_code", 0)
                    )

        raise AIProviderError(
            f"Seluruh Gemini API Key yang dicoba gagal. Error terakhir: {last_exception}"
        )

    async def _auto_detect_and_save_memory(self, telegram_id: int, prompt: str) -> None:
        """Otomatis deteksi jika pesan mengandung instruksi/aturan gaya bahasa atau fakta."""
        p_lower = prompt.lower()
        patterns = [
            r"(?:mulai sekarang|seterusnya|pake|pakai|gunakan)\s+(bahasa\s+\w+|gaya\s+\w+|santai|gaul|non-formal|formal)",
            r"(?:ingat|catat|ingatlah)\s+bahwa\s+(.+)",
            r"(?:panggil\s+saya|panggil\s+aku)\s+(.+)",
        ]
        for pat in patterns:
            match = re.search(pat, p_lower)
            if match:
                content = prompt.strip()
                await self.repo.add_memory(telegram_id, content, memory_type="rule")
                logger.info("Memori jangka panjang baru otomatis dicatat.", telegram_id=telegram_id, content=content)
                break

    def _format_markdown_to_telegram_html(self, text: str) -> str:
        """Konversi format Markdown standar dari AI menjadi HTML yang aman untuk Telegram."""
        if not text:
            return ""

        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def _code_block(match: re.Match) -> str:
            code_content = match.group(2).strip()
            return f"<pre><code>{code_content}</code></pre>"

        text = re.sub(r"```(\w+)?\n(.*?)```", _code_block, text, flags=re.DOTALL)
        text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^\*\n]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*([^\*\n]+)\*", r"<i>\1</i>", text)
        text = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", text)

        return text
