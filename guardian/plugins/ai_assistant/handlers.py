"""Handlers untuk plugin ai_assistant dengan Hermes Memory System, Groq Backup, & Dynamic Skill Engine."""

import re
import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from guardian.plugins.ai_assistant.service import AIAssistantService
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import build_sub_dashboard_keyboard
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class AIAssistantHandlers:
    """Handlers untuk plugin ai_assistant."""

    def __init__(self, service: AIAssistantService) -> None:
        self.service = service

    def _extract_clean_keys(self, raw_input: str) -> list[str]:
        """Ekstrak API Key bersih dari input teks, mengabaikan komentar # ... atau label tambahan."""
        clean_keys = []
        lines = raw_input.splitlines()
        for line in lines:
            line_clean = line.split("#")[0].split("//")[0].strip()
            if not line_clean:
                continue
            tokens = line_clean.split()
            for tok in tokens:
                t = tok.strip()
                if len(t) >= 10 and not t.startswith("/") and not t.lower() in ("addkey", "addkeys", "addgroq", "groqadd"):
                    clean_keys.append(t)
        return clean_keys

    async def handle_ask(self, ctx: CommandContext) -> None:
        """Tanya AI Assistant Hermes atau Kelola Key & Skills. Syntax: /ask [pertanyaan|subcommand]"""
        if not ctx.args:
            await self._show_help(ctx)
            return

        sub = ctx.args[0].lower()
        sub_args = ctx.args[1:]

        if sub == "remember":
            await self._handle_remember(ctx, sub_args)
        elif sub == "memory":
            await self._handle_show_memory(ctx)
        elif sub == "forget":
            await self._handle_forget(ctx, sub_args)
        elif sub == "clear":
            await self._handle_clear_chat(ctx)
        elif sub in ("addkey", "addkeys"):
            await self._handle_add_keys(ctx, sub_args)
        elif sub in ("keys", "keylist", "listkeys"):
            await self._handle_list_keys(ctx)
        elif sub in ("addgroq", "groqadd"):
            await self._handle_add_groq_keys(ctx, sub_args)
        elif sub in ("groqkeys", "groq"):
            await self._handle_list_groq_keys(ctx)
        elif sub in ("delkey", "deletekey", "removekey"):
            await self._handle_delete_key(ctx, sub_args)
        elif sub in ("delgroq", "deletegroq", "removegroq"):
            await self._handle_delete_groq_key(ctx, sub_args)
        elif sub in ("clearkeys", "clean"):
            await self._handle_clear_keys(ctx)
        else:
            await self._handle_chat_query(ctx)

    async def handle_skill(self, ctx: CommandContext) -> None:
        """Handler utama untuk manajemen Hermes Dynamic Skill Engine (/skill)."""
        if not ctx.args:
            await self._handle_list_skills(ctx)
            return

        sub = ctx.args[0].lower()
        args = ctx.args[1:]

        if sub == "add":
            await self._handle_add_skill(ctx, args)
        elif sub in ("list", "show"):
            await self._handle_list_skills(ctx)
        elif sub == "edit":
            await self._handle_edit_skill(ctx, args)
        elif sub in ("del", "delete", "remove"):
            await self._handle_delete_skill(ctx, args)
        elif sub in ("toggle", "switch"):
            await self._handle_toggle_skill(ctx, args)
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "❌ <b>Format Perintah Skill:</b>\n"
                "• <code>/skill add [Nama] | [Deskripsi] | [Instruksi]</code>\n"
                "• <code>/skill list</code>\n"
                "• <code>/skill edit [ID] | [Instruksi Baru]</code>\n"
                "• <code>/skill del [ID]</code>\n"
                "• <code>/skill toggle [ID]</code>",
            )

    async def _show_help(self, ctx: CommandContext) -> None:
        """Tampilkan bantuan AI Assistant, Hermes Memory, Groq Backup & Skill Engine."""
        gemini_stats = await self.service.repo.get_keys_stats()
        groq_stats = await self.service.repo.get_groq_stats()
        skills = await self.service.repo.get_skills(active_only=True)

        key_info = (
            f"🔑 <b>Gemini Key Pool:</b> <code>{gemini_stats['active_keys']} Aktif</code> / <code>{gemini_stats['total_keys']} Total</code>\n"
            f"⚡ <b>Groq Backup Pool:</b> <code>{groq_stats['active_keys']} Aktif</code> (Llama 3.3 70B)\n"
            f"🛠️ <b>Dynamic Skills:</b> <code>{len(skills)} Skill Aktif</code>"
        )

        msg = (
            "🤖 <b>Serverinka AI Assistant (Hermes Engine)</b>\n\n"
            f"{key_info}\n\n"
            "<b>Penggunaan AI Chat:</b>\n"
            "• <code>/ask [pertanyaan]</code> — Tanya AI dengan memori & konteks VPS real-time\n"
            "• Ketik chat biasa (misal: <code>halo</code>) — Langsung dijawab oleh AI!\n\n"
            "🛠️ <b>Hermes Dynamic Skill Engine:</b>\n"
            "• <code>/skill add [Nama] | [Deskripsi] | [Instruksi]</code> — Buat skill baru\n"
            "• <code>/skill list</code> — Lihat daftar seluruh skill AI\n"
            "• <code>/skill edit [ID] | [Instruksi]</code> — Edit instruksi skill\n"
            "• <code>/skill del [ID]</code> — Hapus skill\n\n"
            "🔑 <b>Manajemen Token & Key Pool (SQLite):</b>\n"
            "• <code>/ai addkey [key1] [key2] ...</code> — Tambah Gemini API Key\n"
            "• <code>/ai addgroq [key1] [key2] ...</code> — Tambah Groq API Key (Backup)\n"
            "• <code>/ai keys</code> — Lihat status Gemini Key Pool\n"
            "• <code>/ai groqkeys</code> — Lihat status Groq Backup Pool"
        )
        kb = build_sub_dashboard_keyboard([
            [
                InlineKeyboardButton("🛠️ Daftar Skill AI", callback_data="ask:skills"),
                InlineKeyboardButton("🔑 Gemini Key Pool", callback_data="ask:keys"),
            ],
            [
                InlineKeyboardButton("⚡ Groq Backup Pool", callback_data="ask:groqkeys"),
                InlineKeyboardButton("🧠 Memori AI", callback_data="ask:memory"),
            ]
        ])
        await ctx.respond(msg, keyboard=kb)

    async def _handle_chat_query(self, ctx: CommandContext) -> None:
        """Proses percakapan utama dengan AI."""
        user_prompt = " ".join(ctx.args).strip()
        if not user_prompt:
            raw = ctx.raw_text.strip()
            for prefix in ("/ask", "/ai", "/skill"):
                if raw.lower().startswith(prefix):
                    user_prompt = raw[len(prefix):].strip()
                    break
            if not user_prompt:
                user_prompt = raw

        if not user_prompt:
            await self._show_help(ctx)
            return

        await ctx.bot_gateway.send_chat_action(ctx.chat_id, "typing")

        loading_msg = await ctx.bot_gateway.send_message(
            ctx.chat_id, "🧠 <i>Serverinka AI sedang berpikir & mengingat konteks...</i>"
        )

        try:
            response_text = await self.service.ask_ai(ctx.user.telegram_id, user_prompt)
            formatted_text = f"🤖 <b>Serverinka AI</b>\n\n{response_text}"
            kb = build_sub_dashboard_keyboard()

            if loading_msg:
                await ctx.bot_gateway.edit_message(
                    ctx.chat_id, loading_msg.message_id, formatted_text, keyboard=kb
                )
            else:
                await ctx.bot_gateway.send_message(ctx.chat_id, formatted_text, keyboard=kb)

        except (AIProviderNotConfiguredError, AIProviderError) as e:
            error_text = f"❌ <b>AI Assistant Error:</b>\n\n{escape_html(str(e))}"
            if loading_msg:
                await ctx.bot_gateway.edit_message(ctx.chat_id, loading_msg.message_id, error_text)
            else:
                await ctx.bot_gateway.send_message(ctx.chat_id, error_text)
        except Exception as e:
            logger.exception("Gagal memproses AI chat.", error=str(e))
            if loading_msg:
                await ctx.bot_gateway.edit_message(
                    ctx.chat_id, loading_msg.message_id, "❌ Terjadi kesalahan pada AI Service."
                )

    # ---- GROQ KEY POOL HANDLERS ----

    async def _handle_add_groq_keys(self, ctx: CommandContext, args: list[str]) -> None:
        """Tambah Groq API Key ke SQLite Key Pool."""
        raw_input = " ".join(args).strip()
        if not raw_input:
            raw_input = ctx.raw_text.strip()
            for pfx in ("/ai addgroq", "/ai groqadd", "/ask addgroq"):
                if raw_input.lower().startswith(pfx):
                    raw_input = raw_input[len(pfx):].strip()
                    break

        if not raw_input:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "❌ <b>Format Salah.</b>\n\n"
                "Gunakan format:\n"
                "<code>/ai addgroq gsk_key1 gsk_key2 gsk_key3 ...</code>\n\n"
                "<i>Groq AI digunakan sebagai backup otomatis saat Gemini habis kuota (Model: Llama 3.3 70B Versatile).</i>",
            )
            return

        keys = self._extract_clean_keys(raw_input)

        if not keys:
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Tidak ada API Key Groq valid yang ditemukan.")
            return

        added, duplicates = await self.service.repo.add_groq_keys(keys, model="llama-3.3-70b-versatile")
        stats = await self.service.repo.get_groq_stats()

        msg = (
            f"⚡ <b>Berhasil Memproses Groq Backup Key Pool!</b>\n\n"
            f"📥 <b>Diterima:</b> <code>{len(keys)} Key</code>\n"
            f"➕ <b>Ditambahkan ke SQLite:</b> <code>{added} Key</code>\n"
            f"⚠️ <b>Duplikat/Diabaikan:</b> <code>{duplicates} Key</code>\n\n"
            f"📊 <b>Status Groq Backup Pool:</b>\n"
            f"• Key Aktif: <code>{stats['active_keys']} / {stats['total_keys']}</code>\n"
            f"• Model Default: <code>llama-3.3-70b-versatile</code>\n\n"
            f"<i>Jika seluruh key Gemini habis kuota, AI otomatis berpindah ke Groq tanpa memutus chat!</i>"
        )
        kb = build_sub_dashboard_keyboard([
            [InlineKeyboardButton("⚡ Lihat Groq Backup Pool", callback_data="ask:groqkeys")]
        ])
        await ctx.respond(msg, keyboard=kb)

    async def _handle_list_groq_keys(self, ctx: CommandContext) -> None:
        """Lihat status & kesehatan Groq Key Pool beserta ID dan Error Count."""
        stats = await self.service.repo.get_groq_stats()
        all_keys = await self.service.repo.get_all_groq_keys(limit=30)

        lines = [
            "⚡ <b>Statistik Groq Backup Key Pool (SQLite)</b>\n",
            f"🟢 <b>Key Aktif:</b> <code>{stats['active_keys']}</code> | 📦 <b>Total:</b> <code>{stats['total_keys']}</code> | ⚡ <b>Total Use:</b> <code>{stats['total_usage']}</code>\n",
            "📋 <b>Daftar Groq Key & Jumlah Error:</b>",
        ]

        if not all_keys:
            lines.append("<i>Belum ada Groq API Key terdaftar.</i>")
        else:
            for k in all_keys:
                status_icon = "🟢" if k["is_active"] == 1 else "🔴"
                err_str = f"⚠️ Err: {k['error_count']}" if k['error_count'] > 0 else "✅ No Err"
                lines.append(
                    f"{status_icon} <b>[ID #{k['id']}]</b> <code>{k['api_key_masked']}</code> | {err_str} | Use: {k['usage_count']}"
                )

        lines.append("\n💡 <i>Gunakan <code>/ai delgroq [ID]</code> untuk menghapus key Groq tertentu.</i>")
        lines.append("💡 <i>Gunakan <code>/ai clearkeys</code> untuk pembersihan massal 1-klik!</i>")

        kb = build_sub_dashboard_keyboard([
            [InlineKeyboardButton("🔑 Gemini Key Pool", callback_data="ask:keys")]
        ])
        await ctx.respond("\n".join(lines), keyboard=kb)

    # ---- HERMES DYNAMIC SKILL ENGINE HANDLERS ----

    async def _handle_add_skill(self, ctx: CommandContext, args: list[str]) -> None:
        """Tambah skill AI baru. Format: /skill add <Nama> | <Deskripsi> | <Instruksi>"""
        raw_input = " ".join(args).strip()
        parts = [p.strip() for p in raw_input.split("|") if p.strip()]

        if len(parts) < 2:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "❌ <b>Format Tambah Skill Salah.</b>\n\n"
                "Gunakan tanda <code>|</code> sebagai pemisah:\n"
                "<code>/skill add Nama Skill | Deskripsi | Instruksi Detail Wajib AI</code>\n\n"
                "Contoh:\n"
                "<code>/skill add Penghemat RAM | Analisis hemat RAM | Selalu berikan 3 langkah optimasi RAM terbanyak</code>",
            )
            return

        name = parts[0]
        desc = parts[1] if len(parts) > 2 else "Skill Kustom"
        instructions = parts[2] if len(parts) > 2 else parts[1]

        sk = await self.service.repo.add_skill(skill_name=name, description=desc, instructions=instructions)

        msg = (
            f"🛠️ <b>Hermes Skill Berhasil Dibuat!</b>\n\n"
            f"<b>ID Skill:</b> <code>#{sk['id']}</code>\n"
            f"<b>Nama Skill:</b> <b>{escape_html(sk['skill_name'])}</b>\n"
            f"<b>Deskripsi:</b> <i>{escape_html(sk['description'])}</i>\n"
            f"<b>Instruksi:</b> <code>{escape_html(sk['instructions'])}</code>\n\n"
            f"<i>AI akan langsung mengadopsi dan mematuhi skill ini pada percakapan mendatang!</i>"
        )
        kb = build_sub_dashboard_keyboard([
            [InlineKeyboardButton("🛠️ Lihat Seluruh Skill", callback_data="ask:skills")]
        ])
        await ctx.respond(msg, keyboard=kb)

    async def _handle_list_skills(self, ctx: CommandContext) -> None:
        """Lihat daftar seluruh Hermes Dynamic Skills."""
        skills = await self.service.repo.get_skills(active_only=False)
        if not skills:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "🛠️ <b>Belum ada Hermes Dynamic Skill yang terdaftar.</b>\n\n"
                "Buat skill pertama Anda dengan perintah:\n"
                "<code>/skill add Nama Skill | Deskripsi | Instruksi Detail</code>",
            )
            return

        lines = ["🛠️ <b>Daftar Hermes Dynamic Skills (AI Capabilities)</b>\n"]
        for sk in skills:
            status_icon = "🟢" if sk["is_active"] == 1 else "🔴"
            lines.append(
                f"{status_icon} <b>ID #{sk['id']} — {escape_html(sk['skill_name'])}</b>\n"
                f"📝 <i>{escape_html(sk['description'] or 'Tanpa deskripsi')}</i>\n"
                f"📋 <code>{escape_html(sk['instructions'])}</code>\n"
            )

        lines.append(
            "\n<i>Gunakan:</i>\n"
            "• <code>/skill edit [ID] | [Instruksi Baru]</code>\n"
            "• <code>/skill toggle [ID]</code> — Aktif/nonaktifkan\n"
            "• <code>/skill del [ID]</code> — Hapus skill"
        )
        kb = build_sub_dashboard_keyboard()
        await ctx.respond("\n".join(lines), keyboard=kb)

    async def _handle_edit_skill(self, ctx: CommandContext, args: list[str]) -> None:
        """Edit instruksi skill tertentu. Format: /skill edit <ID> | <Instruksi Baru>"""
        raw_input = " ".join(args).strip()
        parts = [p.strip() for p in raw_input.split("|", 1) if p.strip()]

        if len(parts) < 2 or not parts[0].isdigit():
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format Edit: <code>/skill edit [ID_Skill] | [Instruksi Baru]</code>"
            )
            return

        skill_id = int(parts[0])
        new_instructions = parts[1]

        ok = await self.service.repo.update_skill(skill_id, new_instructions)
        if ok:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"✅ Instruksi skill <b>#{skill_id}</b> berhasil diperbarui!"
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Skill <b>#{skill_id}</b> tidak ditemukan."
            )

    async def _handle_delete_skill(self, ctx: CommandContext, args: list[str]) -> None:
        """Hapus skill berdasarkan ID."""
        if not args or not args[0].isdigit():
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/skill del [ID_Skill]</code>"
            )
            return

        skill_id = int(args[0])
        ok = await self.service.repo.delete_skill(skill_id)
        if ok:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"🗑️ Skill <b>#{skill_id}</b> berhasil dihapus dari SQLite."
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Skill <b>#{skill_id}</b> tidak ditemukan."
            )

    async def _handle_toggle_skill(self, ctx: CommandContext, args: list[str]) -> None:
        """Toggle status aktif/nonaktif skill."""
        if not args or not args[0].isdigit():
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/skill toggle [ID_Skill]</code>"
            )
            return

        skill_id = int(args[0])
        ok = await self.service.repo.toggle_skill(skill_id)
        if ok:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"🔄 Status aktif/nonaktif skill <b>#{skill_id}</b> berhasil diubah."
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Skill <b>#{skill_id}</b> tidak ditemukan."
            )

    # ---- EXISTING GEMINI & MEMORY HANDLERS ----

    async def _handle_add_keys(self, ctx: CommandContext, args: list[str]) -> None:
        """Tambah 1 hingga 100+ Gemini API Key ke SQLite Key Pool."""
        raw_input = " ".join(args).strip()
        if not raw_input:
            raw_input = ctx.raw_text.strip()
            for pfx in ("/ai addkey", "/ai addkeys", "/ask addkey", "/ask addkeys"):
                if raw_input.lower().startswith(pfx):
                    raw_input = raw_input[len(pfx):].strip()
                    break

        if not raw_input:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "❌ <b>Format Salah.</b>\n\n"
                "Gunakan format:\n"
                "<code>/ai addkey AIzaSyKey1 AIzaSyKey2 AIzaSyKey3 ...</code>",
            )
            return

        keys = self._extract_clean_keys(raw_input)

        if not keys:
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Tidak ada API Key valid yang ditemukan.")
            return

        added, duplicates = await self.service.repo.add_api_keys(keys)
        stats = await self.service.repo.get_keys_stats()

        msg = (
            f"✅ <b>Berhasil Memproses Gemini API Key Pool!</b>\n\n"
            f"📥 <b>Diterima:</b> <code>{len(keys)} Key</code>\n"
            f"➕ <b>Ditambahkan ke SQLite:</b> <code>{added} Key</code>\n"
            f"⚠️ <b>Duplikat/Diabaikan:</b> <code>{duplicates} Key</code>\n\n"
            f"📊 <b>Status Key Pool Saat Ini:</b>\n"
            f"• Key Aktif: <code>{stats['active_keys']} / {stats['total_keys']}</code>\n"
        )
        kb = build_sub_dashboard_keyboard([
            [InlineKeyboardButton("🔑 Lihat Seluruh Key Pool", callback_data="ask:keys")]
        ])
        await ctx.respond(msg, keyboard=kb)

    async def _handle_list_keys(self, ctx: CommandContext) -> None:
        """Lihat status & kesehatan Gemini Key Pool di SQLite beserta ID dan Error Count."""
        stats = await self.service.repo.get_keys_stats()
        all_keys = await self.service.repo.get_all_gemini_keys(limit=30)

        lines = [
            "🔑 <b>Statistik SQLite Gemini API Key Pool</b>\n",
            f"🟢 <b>Key Aktif:</b> <code>{stats['active_keys']}</code> | 🔴 <b>Mati:</b> <code>{stats['inactive_keys']}</code> | 📦 <b>Total:</b> <code>{stats['total_keys']}</code>",
            f"⚡ <b>Total Permintaan:</b> <code>{stats['total_usage']} request</code>\n",
            "📋 <b>Daftar Gemini Key & Jumlah Error:</b>",
        ]

        if not all_keys:
            lines.append("<i>Belum ada Gemini API Key terdaftar.</i>")
        else:
            for k in all_keys:
                status_icon = "🟢" if k["is_active"] == 1 else "🔴"
                err_str = f"⚠️ Err: {k['error_count']}" if k['error_count'] > 0 else "✅ No Err"
                lines.append(
                    f"{status_icon} <b>[ID #{k['id']}]</b> <code>{k['api_key_masked']}</code> | {err_str} | Use: {k['usage_count']}"
                )

        lines.append("\n💡 <i>Gunakan <code>/ai delkey [ID]</code> untuk menghapus key Gemini tertentu.</i>")
        lines.append("💡 <i>Gunakan <code>/ai clearkeys</code> untuk pembersihan massal 1-klik!</i>")

        kb = build_sub_dashboard_keyboard([
            [InlineKeyboardButton("⚡ Groq Backup Pool", callback_data="ask:groqkeys")]
        ])
        await ctx.respond("\n".join(lines), keyboard=kb)

    async def _handle_delete_key(self, ctx: CommandContext, args: list[str]) -> None:
        """Hapus key Gemini tertentu berdasarkan ID atau string Key."""
        if not args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/ai delkey [ID|API_Key]</code>"
            )
            return

        ok = await self.service.repo.delete_key(args[0])
        if ok:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"🗑️ Gemini API Key <code>{escape_html(args[0])}</code> berhasil dihapus dari SQLite."
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Gemini API Key <code>{escape_html(args[0])}</code> tidak ditemukan."
            )

    async def _handle_delete_groq_key(self, ctx: CommandContext, args: list[str]) -> None:
        """Hapus key Groq tertentu berdasarkan ID atau string Key."""
        if not args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/ai delgroq [ID|API_Key]</code>"
            )
            return

        ok = await self.service.repo.delete_groq_key(args[0])
        if ok:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"🗑️ Groq API Key <code>{escape_html(args[0])}</code> berhasil dihapus dari SQLite."
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Groq API Key <code>{escape_html(args[0])}</code> tidak ditemukan."
            )

    async def _handle_clear_keys(self, ctx: CommandContext) -> None:
        """Pembersihan massal seluruh key mati/error (Gemini & Groq)."""
        cnt_gemini = await self.service.repo.clear_inactive_keys()
        cnt_groq = await self.service.repo.clear_inactive_groq_keys()
        await ctx.bot_gateway.send_message(
            ctx.chat_id,
            f"🧹 <b>Pembersihan Key Mati Selesai!</b>\n\n"
            f"🗑️ <b>Gemini Key Dihapus:</b> <code>{cnt_gemini} Key</code>\n"
            f"🗑️ <b>Groq Key Dihapus:</b> <code>{cnt_groq} Key</code>",
        )

    async def _handle_remember(self, ctx: CommandContext, args: list[str]) -> None:
        """Simpan aturan / memori baru secara manual."""
        if not args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/ask remember [aturan/instruksi/fakta]</code>"
            )
            return
        content = " ".join(args)
        mem = await self.service.repo.add_memory(ctx.user.telegram_id, content, memory_type="rule")
        await ctx.bot_gateway.send_message(
            ctx.chat_id,
            f"🧠 <b>Memori Berhasil Disimpan!</b>\n\n"
            f"<b>ID:</b> <code>{mem.id}</code>\n"
            f"<b>Aturan/Memori:</b> <i>{escape_html(mem.content)}</i>\n\n"
            f"<i>AI akan selalu mengingat dan mematuhi aturan ini pada setiap percakapan.</i>",
        )

    async def _handle_show_memory(self, ctx: CommandContext) -> None:
        """Tampilkan seluruh memori tersimpan."""
        memories = await self.service.repo.get_memories(ctx.user.telegram_id)
        if not memories:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "🧠 <b>Belum ada memori atau aturan khusus yang tersimpan.</b>"
            )
            return

        lines = ["🧠 <b>Daftar Memori & Aturan AI Tersimpan (Hermes Memory)</b>\n"]
        for m in memories:
            lines.append(f"• <b>ID {m.id}</b> [{m.memory_type.upper()}]: <i>{escape_html(m.content)}</i>")

        lines.append("\n<i>Gunakan <code>/ask forget [ID]</code> untuk menghapus memori tertentu.</i>")
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines))

    async def _handle_forget(self, ctx: CommandContext, args: list[str]) -> None:
        """Hapus memori jangka panjang."""
        if not args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/ask forget [ID_Memori|all]</code>"
            )
            return

        target = args[0].lower()
        if target == "all":
            cnt = await self.service.repo.clear_memories(ctx.user.telegram_id)
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"🗑️ Berhasil menghapus seluruh {cnt} memori tersimpan."
            )
        elif target.isdigit():
            mem_id = int(target)
            ok = await self.service.repo.delete_memory(ctx.user.telegram_id, mem_id)
            if ok:
                await ctx.bot_gateway.send_message(
                    ctx.chat_id, f"🗑️ Memori ID <code>{mem_id}</code> berhasil dihapus."
                )
            else:
                await ctx.bot_gateway.send_message(
                    ctx.chat_id, f"❌ Memori ID <code>{mem_id}</code> tidak ditemukan."
                )
        else:
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Masukkan ID angka atau 'all'.")

    async def _handle_clear_chat(self, ctx: CommandContext) -> None:
        """Reset histori percakapan singkat."""
        cnt = await self.service.repo.clear_chat_history(ctx.user.telegram_id)
        await ctx.bot_gateway.send_message(
            ctx.chat_id, f"🧹 Histori percakapan singkat berhasil direset ({cnt} pesan dihapus)."
        )
