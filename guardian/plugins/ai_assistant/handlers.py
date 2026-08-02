"""Handlers untuk plugin ai_assistant dengan Hermes Memory System."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from guardian.plugins.ai_assistant.service import AIAssistantService
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import nav_row
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class AIAssistantHandlers:
    """Handlers untuk plugin ai_assistant."""

    def __init__(self, service: AIAssistantService) -> None:
        self.service = service

    async def handle_ask(self, ctx: CommandContext) -> None:
        """Tanya AI Assistant Hermes. Syntax: /ask [pertanyaan|subcommand]"""
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
        else:
            await self._handle_chat_query(ctx)

    async def _show_help(self, ctx: CommandContext) -> None:
        """Tampilkan bantuan AI Assistant & Hermes Memory."""
        msg = (
            "🤖 <b>Serverinka AI Assistant (Hermes Engine)</b>\n\n"
            "<b>Penggunaan Utama:</b>\n"
            "• <code>/ask [pertanyaan]</code> — Tanya AI dengan memori & konteks VPS real-time\n\n"
            "🧠 <b>Manajemen Memori (Hermes System):</b>\n"
            "• <code>/ask remember [aturan/fakta]</code> — Catat memori / gaya bahasa / instruksi khusus\n"
            "• <code>/ask memory</code> — Lihat seluruh memori & aturan tersimpan\n"
            "• <code>/ask forget [ID|all]</code> — Hapus memori tersimpan\n"
            "• <code>/ask clear</code> — Reset histori percakapan singkat"
        )
        await ctx.bot_gateway.send_message(ctx.chat_id, msg)

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
            kb = InlineKeyboardMarkup([nav_row(main_menu=True)])

            if loading_msg:
                await ctx.bot_gateway.edit_message(
                    ctx.chat_id, loading_msg.message_id, formatted_text, keyboard=kb
                )
            else:
                await ctx.bot_gateway.send_message(ctx.chat_id, formatted_text, keyboard=kb)

        except (AIProviderNotConfiguredError, AIProviderError) as e:
            error_text = f"❌ <b>AI Assistant Error:</b> {escape_html(e.message)}"
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
            ctx.chat_id, "🧹 <b>Histori percakapan singkat berhasil dibersihkan!</b> (Konteks percakapan di-reset)."
        )
