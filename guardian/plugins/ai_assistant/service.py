"""Service cerdas untuk AI Assistant dengan Hermes Memory System, Dynamic Skill Engine, & Groq Backup Integration."""

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
    """Service AI Assistant cerdas berbasis Hermes Memory & Dynamic Skill Engine."""

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
            message="AI Assistant Hermes Memory & Skill Engine Siap." if status == "healthy" else "AI Assistant Disabled.",
            checked_at=datetime.utcnow(),
        )

    async def build_system_context_prompt(self, telegram_id: int) -> str:
        """Kumpulkan statistik VPS real-time, Long-Term Memory, dan Dynamic Skills."""
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

        # 1. Long-Term Memories & User Rules
        memories = await self.repo.get_memories(telegram_id)
        memory_lines = []
        if memories:
            for mem in memories:
                memory_lines.append(f"- [{mem.memory_type.upper()}] {mem.content}")
        memory_str = "\n".join(memory_lines) if memory_lines else "Belum ada memori khusus tersimpan."

        # 2. Dynamic Hermes Skills
        skills = await self.repo.get_skills(active_only=True)
        skill_lines = []
        if skills:
            for sk in skills:
                skill_lines.append(
                    f"🛠️ [SKILL #{sk['id']}: {sk['skill_name'].upper()}]\n"
                    f"Deskripsi: {sk['description'] or 'N/A'}\n"
                    f"Instruksi Wajib: {sk['instructions']}\n"
                )
        skill_str = "\n".join(skill_lines) if skill_lines else "Tidak ada skill custom aktif."

        docker_info = "Aktif" if self._ctx.settings.docker_enabled else "Non-Aktif"
        cpu_guard_info = f"Aktif (Batas {self._ctx.settings.cpu_usage_limit}%)"

        system_prompt = (
            f"Anda adalah 'Serverinka AI', asisten AI super pintar pengelola VPS berbasis Google Gemini & Groq Llama 3.3.\n\n"
            f"🧠 MEMORI JANGKA PANJANG & ATURAN PENGGUNA (HERMES MEMORY SYSTEM):\n"
            f"{memory_str}\n\n"
            f"⚙️ KEMAMPUAN & SKILL KUSTOM DARI USER (HERMES DYNAMIC SKILL ENGINE):\n"
            f"{skill_str}\n\n"
            f"📊 METRIK & STATUS VPS REAL-TIME SAAT INI:\n"
            f"• CPU Usage: {m['cpu_percent']}% ({m['cpu_count']} Cores)\n"
            f"• RAM Usage: {m['ram_used']} / {m['ram_total']} ({m['ram_percent']}%)\n"
            f"• Disk Usage: {m['disk_used']} / {m['disk_total']} ({m['disk_percent']}%)\n"
            f"• Uptime VPS: {m['uptime']}\n"
            f"• Docker Integration: {docker_info}\n"
            f"• CPU Guard: {cpu_guard_info}\n\n"
            f"PEDOMAN RESPON:\n"
            f"1. PATUHI SELURUH MEMORI DAN SKILL KUSTOM DI ATAS. Jika ada skill khusus yang cocok dengan permintaan user, jalankan instruksi skill tersebut secara ketat!\n"
            f"2. Gunakan status VPS real-time untuk menjawab pertanyaan teknis.\n"
            f"3. Berikan balasan yang jelas, solutif, dan ramah."
        )
        return system_prompt

    async def ask_ai(
        self,
        telegram_id: int,
        user_prompt: str,
        media_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> str:
        """Kirim pertanyaan pengguna ke AI dengan memori, konteks histori percakapan, & Multimodal Media."""
        # 0. Otomatis deteksi jika pesan berisi API key (pesan terpotong Telegram)
        if not media_bytes:
            auto_imported = await self._auto_detect_and_import_keys(user_prompt)
            if auto_imported:
                return auto_imported

            # 1. Otomatis deteksi jika user memberikan instruksi/memori baru atau jadwal pengingat
            await self._auto_detect_and_save_memory(telegram_id, user_prompt)
            await self._auto_detect_and_schedule_task(telegram_id, user_prompt)

        # 2. Ambil histori percakapan (Short-Term Memory)
        history = await self.repo.get_recent_chat_history(telegram_id, limit=8)
        messages = [{"role": h.role, "content": h.content} for h in history]
        messages.append({"role": "user", "content": user_prompt})

        # 3. Buat System Prompt dengan statistik VPS, Memori, & Skills
        system_prompt = await self.build_system_context_prompt(telegram_id)

        # 4. Panggil AI Client dengan Multi-Tier Rotation (Gemini Pool -> Groq Backup Pool -> Config)
        raw_response = await self._call_ai_with_multi_tier_fallback(
            messages=messages,
            system_prompt=system_prompt,
            media_bytes=media_bytes,
            mime_type=mime_type,
        )

        # 5. Simpan percakapan ke Short-Term Memory
        await self.repo.add_chat_turn(telegram_id, "user", user_prompt)
        await self.repo.add_chat_turn(telegram_id, "assistant", raw_response)

        return self._format_markdown_to_telegram_html(raw_response)

    async def _call_ai_with_multi_tier_fallback(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        media_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> str:
        """Multi-Tier Provider Fallback Router: Gemini Pool -> Groq Backup Pool -> Config Fallback."""
        last_exception: Exception | None = None

        # ---- TIER 1: GOOGLE GEMINI SQLITE KEY POOL ----
        max_gemini_attempts = 5
        for attempt in range(max_gemini_attempts):
            api_key = await self.repo.get_next_active_key()
            if not api_key:
                break

            try:
                raw_response = await self.ai_client.chat_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    api_key=api_key,
                    provider="gemini",
                    temperature=0.7,
                    media_bytes=media_bytes,
                    mime_type=mime_type,
                )
                await self.repo.record_key_success(api_key)
                return raw_response
            except AIProviderError as e:
                last_exception = e
                logger.warning(
                    "Gemini API Key bermasalah, beralih ke key Gemini berikutnya...",
                    attempt=attempt + 1,
                    api_key_prefix=api_key[:10],
                    error=str(e),
                )
                await self.repo.record_key_error(api_key, str(e), getattr(e, "status_code", 0))

        # ---- TIER 2: GROQ AI BACKUP SQLITE KEY POOL (Llama 3.3 70B & Vision) ----
        max_groq_attempts = 5
        for attempt in range(max_groq_attempts):
            groq_key, groq_model = await self.repo.get_next_groq_key()
            if not groq_key:
                break

            try:
                logger.info("Menggunakan Backup Provider Groq AI...", model=groq_model)
                raw_response = await self.ai_client.chat_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    api_key=groq_key,
                    provider="groq",
                    model=groq_model or "llama-3.3-70b-versatile",
                    temperature=0.7,
                    media_bytes=media_bytes,
                    mime_type=mime_type,
                )
                await self.repo.record_groq_success(groq_key)
                return raw_response
            except AIProviderError as e:
                last_exception = e
                logger.warning(
                    "Groq API Key bermasalah, mencoba key Groq berikutnya...",
                    attempt=attempt + 1,
                    error=str(e),
                )
                await self.repo.record_groq_error(groq_key, str(e), getattr(e, "status_code", 0))

        # ---- TIER 3: CONFIG FALLBACK AI API KEY ----
        config_key = self._ctx.settings.ai_api_key
        if config_key:
            try:
                return await self.ai_client.chat_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    api_key=config_key,
                    provider=self._ctx.settings.ai_provider,
                    temperature=0.7,
                )
            except Exception as e:
                last_exception = e

        raise AIProviderNotConfiguredError(
            f"Seluruh provider AI (Gemini & Groq Backup Pool) tidak dapat diakses!\n\n"
            f"Detail error terakhir: {last_exception}\n\n"
            f"Gunakan perintah Telegram berikut untuk memasukkan API Key baru:\n"
            f"• <code>/ai addkey AIzaSy...</code> (Google Gemini)\n"
            f"• <code>/ai addgroq gsk_...</code> (Groq Llama 3.3 70B)"
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

    async def _auto_detect_and_schedule_task(self, telegram_id: int, prompt: str) -> None:
        """Otomatis deteksi jika pesan pengguna mengandung permintaan penjadwalan/pengingat."""
        p_lower = prompt.lower()
        if any(w in p_lower for w in ("ingatkan", "jadwalkan", "remind", "pengingat")):
            try:
                from guardian.plugins.scheduler_ui.service import AISchedulerService
                sched_service = AISchedulerService(self._ctx)

                interval_sec = 600
                if "setiap menit" in p_lower or "tiap menit" in p_lower:
                    interval_sec = 60
                elif "5 menit" in p_lower:
                    interval_sec = 300
                elif "10 menit" in p_lower:
                    interval_sec = 600
                elif "30 menit" in p_lower:
                    interval_sec = 1800
                elif "setiap jam" in p_lower or "tiap jam" in p_lower:
                    interval_sec = 3600

                await sched_service.add_schedule(
                    telegram_id=telegram_id,
                    task_type="interval",
                    message=prompt.strip(),
                    interval_seconds=interval_sec,
                )
                logger.info("Jadwal pengingat AI otomatis terdeteksi & dibuat.", telegram_id=telegram_id, prompt=prompt)
            except Exception as e:
                logger.debug("Gagal auto-detect schedule task.", error=str(e))

    async def _auto_detect_and_import_keys(self, user_prompt: str) -> str | None:
        """Otomatis deteksi jika pesan pengguna adalah tumpukan API Key (misal dari terpotongnya Telegram message)."""
        lines = [l.strip() for l in user_prompt.splitlines() if l.strip()]
        detected_keys = []
        for line in lines:
            clean_line = line.split("#")[0].split("//")[0].strip()
            tokens = clean_line.split()
            for t in tokens:
                if len(t) >= 15 and not t.startswith("/"):
                    detected_keys.append(t)

        if len(detected_keys) >= 1 and any(k.startswith(("AIzaSy", "AQ.", "gsk_")) for k in detected_keys):
            gemini_keys = [k for k in detected_keys if not k.startswith("gsk_")]
            groq_keys = [k for k in detected_keys if k.startswith("gsk_")]

            added_g, dup_g = await self.repo.add_api_keys(gemini_keys) if gemini_keys else (0, 0)
            added_q, dup_q = await self.repo.add_groq_keys(groq_keys) if groq_keys else (0, 0)

            total_added = added_g + added_q
            total_dup = dup_g + dup_q
            return (
                f"✅ <b>Terdeteksi Impor API Key ke SQLite!</b>\n\n"
                f"📥 <b>Diterima:</b> <code>{len(detected_keys)} Key</code>\n"
                f"➕ <b>Ditambahkan:</b> <code>{total_added} Key Baru</code>\n"
                f"⚠️ <b>Duplikat/Diabaikan:</b> <code>{total_dup} Key</code>\n\n"
                f"<i>Seluruh Key telah tersimpan aman di database SQLite VPS Anda.</i>"
            )
        return None

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
