"""Handlers untuk plugin ai_assistant dengan Hermes Memory System & Gemini Key Pool Management."""

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

    async def handle_ask(self, ctx: CommandContext) -> None:
        """Tanya AI Assistant Hermes atau Kelola API Key Pool. Syntax: /ask [pertanyaan|subcommand]"""
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
        elif sub in ("delkey", "deletekey", "removekey"):
            await self._handle_delete_key(ctx, sub_args)
        elif sub in ("clearkeys", "clean"):
            await self._handle_clear_keys(ctx)
        else:
            await self._handle_chat_query(ctx)

    async def _show_help(self, ctx: CommandContext) -> None:
        """Tampilkan bantuan AI Assistant, Hermes Memory & API Key Pool."""
        stats = await self.service.repo.get_keys_stats()
        key_info = (
            f"🔑 <b>Gemini Key Pool (SQLite):</b> <code>{stats['active_keys']} Aktif</code> / <code>{stats['total_keys']} Total</code>"
        )

        msg = (
            "🤖 <b>Serverinka AI Assistant (Google Gemini 2.5 Flash)</b>\n\n"
            f"{key_info}\n\n"
            "<b>Penggunaan AI Chat:</b>\n"
            "• <code>/ask [pertanyaan]</code> — Tanya AI dengan memori & konteks VPS real-time\n"
            "• Ketik chat biasa (misal: <code>halo</code>) — Langsung dijawab oleh AI!\n\n"
            "🔑 <b>Manajemen API Key Pool (SQLite):</b>\n"
            "• <code>/ai addkey [key1] [key2] ...</code> — Tambah 1 hingga 100+ API key Gemini\n"
            "• <code>/ai keys</code> — Lihat statistik & kesehatan Key Pool\n"
            "• <code>/ai delkey [ID|key]</code> — Hapus API Key dari SQLite\n"
            "• <code>/ai clearkeys</code> — Hapus seluruh key mati/kuota habis\n\n"
            "🧠 <b>Manajemen Memori (Hermes System):</b>\n"
            "• <code>/ask remember [aturan]</code> — Catat memori / instruksi khusus\n"
            "• <code>/ask memory</code> — Lihat seluruh memori tersimpan\n"
            "• <code>/ask forget [ID|all]</code> — Hapus memori tersimpan\n"
            "• <code>/ask clear</code> — Reset histori percakapan singkat"
        )
        kb = build_sub_dashboard_keyboard([
            [
                InlineKeyboardButton("🔑 Status Key Pool", callback_data="ask:keys"),
                InlineKeyboardButton("🧠 Memori AI", callback_data="ask:memory"),
            ]
        ])
        await ctx.respond(msg, keyboard=kb)

    async def _handle_chat_query(self, ctx: CommandContext) -> None:
        """Proses percakapan utama dengan AI."""
        user_prompt = " ".join(ctx.args).strip()
        if not user_prompt:
            raw = ctx.raw_text.strip()
            for prefix in ("/ask", "/ai"):
                if raw.lower().startswith(prefix):
                    user_prompt = raw[len(prefix):].strip()
                    break
            if not user_prompt:
                user_prompt = raw

        if not user_prompt:
            await self._show_help(ctx)
            return

        # Kirim indikator typing ke Telegram
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
                "<code>/ai addkey AIzaSyKey1 AIzaSyKey2 AIzaSyKey3 ...</code>\n\n"
                "<i>Anda dapat memasukkan hingga 100+ API Key sekaligus dipisahkan dengan spasi atau baris baru!</i>",
            )
            return

        # Split berdasarkan spasi, koma, atau baris baru
        keys = [k.strip() for k in re.split(r"[\s,\n]+", raw_input) if k.strip()]

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
            f"• Total Key: <code>{stats['total_keys']}</code>\n"
            f"• Key Aktif: <code>{stats['active_keys']}</code>\n"
            f"• Key Mati/Habis Limit: <code>{stats['inactive_keys']}</code>\n\n"
            f"<i>AI akan melakukan Load Balancing & Auto Rotation dari seluruh key aktif di SQLite secara otomatis!</i>"
        )
        kb = build_sub_dashboard_keyboard([
            [InlineKeyboardButton("🔑 Lihat Seluruh Key Pool", callback_data="ask:keys")]
        ])
        await ctx.respond(msg, keyboard=kb)

    async def _handle_list_keys(self, ctx: CommandContext) -> None:
        """Lihat status & kesehatan Key Pool di SQLite."""
        stats = await self.service.repo.get_keys_stats()

        msg = (
            "🔑 <b>Statistik SQLite Gemini API Key Pool</b>\n\n"
            f"🟢 <b>Key Aktif:</b> <code>{stats['active_keys']} Key</code>\n"
            f"🔴 <b>Key Mati (Kuota Habis/Error):</b> <code>{stats['inactive_keys']} Key</code>\n"
            f"📦 <b>Total Key Terdaftar:</b> <code>{stats['total_keys']} Key</code>\n"
            f"⚡ <b>Total Permintaan Ditangani:</b> <code>{stats['total_usage']} request</code>\n\n"
            "<i>Sistem otomatis melakukan failover & rotasi key jika salah satu key mencapai rate limit!</i>"
        )
        kb = build_sub_dashboard_keyboard([
            [
                InlineKeyboardButton("🧹 Bersihkan Key Mati", callback_data="ask:clearkeys"),
                InlineKeyboardButton("🧠 Memori AI", callback_data="ask:memory"),
            ]
        ])
        await ctx.respond(msg, keyboard=kb)

    async def _handle_delete_key(self, ctx: CommandContext, args: list[str]) -> None:
        """Hapus key tertentu berdasarkan ID atau string Key."""
        if not args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/ai delkey [ID|API_Key]</code>"
            )
            return

        ok = await self.service.repo.delete_key(args[0])
        if ok:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"🗑️ API Key <code>{escape_html(args[0])}</code> berhasil dihapus dari SQLite."
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ API Key <code>{escape_html(args[0])}</code> tidak ditemukan."
            )

    async def _handle_clear_keys(self, ctx: CommandContext) -> None:
        """Pembersihan key mati."""
        cnt = await self.service.repo.clear_inactive_keys()
        await ctx.bot_gateway.send_message(
            ctx.chat_id, f"🧹 Berhasil membersihkan <code>{cnt}</code> API key yang dinonaktifkan dari SQLite."
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
