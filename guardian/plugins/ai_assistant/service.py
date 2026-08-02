"""Service cerdas untuk AI Assistant dengan Hermes Long-Term & Short-Term Memory System."""

import asyncio
import os
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import psutil
import structlog

from guardian.core.ai_service import AIService
from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.ai_assistant.repository import AIMemoryRepository
from guardian.utils.formatters import escape_html, format_bytes, format_uptime

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class AIAssistantService(BaseService):
    """Service AI Assistant cerdas berbasis Hermes Memory System."""

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
            message="AI Assistant Hermes Memory Siap." if status == "healthy" else "AI Assistant Disabled.",
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

        # Ambil Memori Jangka Panjang / Aturan User dari Database
        memories = await self.repo.get_memories(telegram_id)
        memory_str = "\n".join([f"• [{mem.memory_type.upper()}] (ID {mem.id}): {mem.content}" for mem in memories])
        if not memory_str:
            memory_str = "Belum ada memori khusus."

        docker_info = "Aktif" if self._ctx.settings.docker_enabled else "Nonaktif"
        cpu_guard_info = f"Aktif (Threshold {self._ctx.settings.cpu_usage_limit}%)"

        system_prompt = (
            f"Kamu adalah Serverinka AI, Asisten Sysadmin VPS Cerdas bereputasi seperti Hermes yang dilengkapi dengan Long-Term Memory System.\n\n"
            f"🧠 MEMORI JANGKA PANJANG & ATURAN PENGGUNA INI:\n"
            f"{memory_str}\n\n"
            f"📊 STATUS VPS SAAT INI (REALTIME):\n"
            f"• Uptime: {m['uptime']}\n"
            f"• CPU Usage: {m['cpu_percent']:.1f}% ({m['cpu_count']} Cores)\n"
            f"• RAM Usage: {m['ram_used']} / {m['ram_total']} ({m['ram_percent']}%)\n"
            f"• Disk Usage: {m['disk_used']} / {m['disk_total']} ({m['disk_percent']}%)\n"
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

        # 4. Panggil AI Gateway
        raw_response = await self.ai_client.chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
        )

        # 5. Simpan percakapan ke Short-Term Memory
        await self.repo.add_chat_turn(telegram_id, "user", user_prompt)
        await self.repo.add_chat_turn(telegram_id, "assistant", raw_response)

        return self._format_markdown_to_telegram_html(raw_response)

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

        text = re.sub(r"```(\w*)\n?(.*?)```", _code_block, text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
        text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
        text = re.sub(r"_([^_]+)_", r"<i>\1</i>", text)

        return text
