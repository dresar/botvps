"""Service cerdas untuk AI Assistant dengan kemampuan System Context & Execution Skill."""

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
from guardian.utils.formatters import escape_html, format_bytes, format_uptime

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class AIAssistantService(BaseService):
    """Service AI Assistant cerdas berpengatahuan penuh atas status VPS & kemampuan eksekusi."""

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self.ai_client = AIService(ctx.settings)

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan AI Service."""
        status = "healthy" if self.ai_client.is_enabled else "degraded"
        return ServiceHealth(
            service_name="AIAssistantService",
            status=status,
            message="AI Assistant Siap." if status == "healthy" else "AI Assistant Disabled.",
            checked_at=datetime.utcnow(),
        )

    async def build_system_context_prompt(self) -> str:
        """Kumpulkan statistik status VPS real-time untuk diinjeksi ke AI system prompt."""
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

        # Cek status Docker & Protection Plugins
        docker_info = "Aktif (Terintegrasi)" if self._ctx.settings.docker_enabled else "Nonaktif"
        cpu_guard_info = f"Aktif (Threshold {self._ctx.settings.cpu_usage_limit}%)"
        package_guard_info = f"Aktif (Blocked: {self._ctx.settings.blocked_packages})"

        system_prompt = (
            f"Kamu adalah Serverinka AI, Asisten Sysadmin VPS Cerdas yang mengelola VPS Serverinka Guardian.\n\n"
            f"STATUS VPS SAAT INI (REALTIME):\n"
            f"• Uptime: {m['uptime']}\n"
            f"• CPU Usage: {m['cpu_percent']:.1f}% ({m['cpu_count']} Cores)\n"
            f"• RAM Usage: {m['ram_used']} / {m['ram_total']} ({m['ram_percent']}%)\n"
            f"• Disk Usage: {m['disk_used']} / {m['disk_total']} ({m['disk_percent']}%)\n"
            f"• Docker Integration: {docker_info}\n"
            f"• Auto Process CPU Guard: {cpu_guard_info}\n"
            f"• Package Protection: {package_guard_info}\n\n"
            f"KEMAMPUAN PERINTAH BOT TELEGRAM:\n"
            f"- /status (Cek statistik VPS)\n"
            f"- /service list | start | stop | restart <service>\n"
            f"- /docker list | start | stop | restart <container>\n"
            f"- /cpu_guard status | top | kill <PID> | whitelist | blacklist\n"
            f"- /package_guard status | scan | uninstall <pkg>\n"
            f"- /user list\n\n"
            f"TUGAS KAMU:\n"
            f"1. Jawab pertanyaan pengguna dengan ramah, profesional, solutif, dan akurat.\n"
            f"2. Gunakan pengetahuan status VPS di atas untuk memberikan jawaban spesifik.\n"
            f"3. Jika pengguna meminta bantuan eksekusi/tindakan (misal restart service atau kill PID), jelaskan langkahnya dan rekomendasikan command yang sesuai."
        )
        return system_prompt

    async def ask_ai(self, user_prompt: str) -> str:
        """Kirim pertanyaan pengguna ke AI dengan konteks VPS real-time."""
        system_prompt = await self.build_system_context_prompt()
        raw_response = await self.ai_client.chat_completion(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.6,
        )
        return self._format_markdown_to_telegram_html(raw_response)

    def _format_markdown_to_telegram_html(self, text: str) -> str:
        """Konversi format Markdown standar dari AI menjadi HTML yang aman untuk Telegram."""
        if not text:
            return ""

        # Escape karakter HTML krusial
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Unescape elemen HTML dasar jika AI sengaja menggunakan tag safe
        # Format Code block ```lang ... ```
        def _code_block(match: re.Match) -> str:
            code_content = match.group(2).strip()
            return f"<pre><code>{code_content}</code></pre>"

        text = re.sub(r"```(\w*)\n?(.*?)```", _code_block, text, flags=re.DOTALL)

        # Format Inline Code `code`
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

        # Format Bold **text** atau __text__
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)

        # Format Italic *text* atau _text_
        text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
        text = re.sub(r"_([^_]+)_", r"<i>\1</i>", text)

        return text
