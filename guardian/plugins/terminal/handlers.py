"""Handlers untuk Terminal Plugin — Full Shell Access via Telegram."""

from datetime import datetime

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.utils.formatters import escape_html

logger = structlog.get_logger(__name__)

# Panjang maksimum output per pesan Telegram sebelum dipecah
_MAX_MSG_CHARS = 3500
_CODE_BLOCK_OVERHEAD = 12  # <pre><code>...</code></pre>


def _format_output_block(output: str) -> str:
    """Bungkus output dalam HTML code block, potong jika perlu."""
    max_content = _MAX_MSG_CHARS - _CODE_BLOCK_OVERHEAD
    if len(output) > max_content:
        output = output[:max_content] + "\n… (output terpotong)"
    return f"<pre><code>{escape_html(output)}</code></pre>"


class TerminalHandlers:
    """Command handlers untuk Terminal Plugin."""

    def _get_service(self, ctx: CommandContext) -> "object":
        from guardian.plugins.terminal.service import TerminalService
        return TerminalService(ctx.app_ctx)

    async def handle_run(self, ctx: CommandContext) -> None:
        """Eksekusi perintah shell dari Telegram.

        Dipanggil via:
          - /run <command>
          - $ <command>    (shortcut prefix dollar)
        """
        from guardian.plugins.terminal.service import TerminalService

        # Ambil perintah dari raw_text atau args
        raw_text = ctx.raw_text.strip()
        cmd = ""

        if raw_text.startswith("$ "):
            cmd = raw_text[2:].strip()
        elif raw_text.startswith("/run"):
            # Ambil sisa setelah /run (+ strip @botname jika ada)
            after_slash = raw_text.split(None, 1)
            cmd = after_slash[1].strip() if len(after_slash) > 1 else ""
        elif ctx.args:
            cmd = " ".join(ctx.args)

        if not cmd:
            await ctx.respond(
                "❌ <b>Perintah kosong.</b>\n\n"
                "Contoh penggunaan:\n"
                "<code>/run ls -la /var/log</code>\n"
                "<code>/run docker ps</code>\n"
                "<code>$ df -h</code>"
            )
            return

        # Kirim indikator "typing"
        await ctx.bot_gateway.send_chat_action(ctx.chat_id, "typing")

        # Kirim pesan loading
        loading_msg = await ctx.bot_gateway.send_message(
            ctx.chat_id,
            f"⚙️ <b>Menjalankan perintah...</b>\n<code>$ {escape_html(cmd)}</code>",
        )

        service = TerminalService(ctx.app_ctx)
        result = await service.execute(ctx.user.telegram_id, cmd)

        # Susun pesan hasil
        if result.blocked:
            response = (
                f"🚫 <b>Perintah Diblokir oleh Danger Guard</b>\n\n"
                f"<code>$ {escape_html(result.command)}</code>\n\n"
                f"⚠️ <i>{escape_html(result.block_reason)}</i>\n\n"
                f"Hubungi admin jika perintah ini seharusnya diizinkan."
            )
        elif result.timed_out:
            response = (
                f"⏱️ <b>Timeout</b>\n\n"
                f"<code>$ {escape_html(result.command)}</code>\n\n"
                f"Perintah melebihi batas waktu eksekusi."
            )
        else:
            status_icon = "✅" if result.success else "❌"
            header = (
                f"{status_icon} <b>Exit Code: {result.exit_code}</b>  "
                f"│  <code>{escape_html(result.cwd)}</code>\n"
                f"<code>$ {escape_html(result.command)}</code>\n\n"
            )
            output = result.combined_output
            truncated_notice = "\n\n⚠️ <i>Output terpotong (terlalu panjang)</i>" if result.truncated else ""
            response = header + _format_output_block(output) + truncated_notice

        from guardian.plugins.terminal.keyboard import build_terminal_keyboard
        keyboard = build_terminal_keyboard()

        if loading_msg:
            await ctx.bot_gateway.edit_message(
                chat_id=ctx.chat_id,
                message_id=loading_msg.message_id,
                text=response,
                keyboard=keyboard,
            )
        else:
            await ctx.bot_gateway.send_message(ctx.chat_id, response, keyboard=keyboard)

    async def handle_history(self, ctx: CommandContext) -> None:
        """Tampilkan 20 perintah terakhir yang dieksekusi user."""
        from guardian.plugins.terminal.repository import TerminalRepository

        repo = TerminalRepository(ctx.app_ctx.database)
        history = await repo.get_history(ctx.user.telegram_id, limit=20)

        if not history:
            await ctx.respond("📋 <b>Riwayat Terminal Kosong</b>\n\nBelum ada perintah yang dieksekusi.")
            return

        lines = ["📋 <b>Riwayat Perintah Terminal (20 Terakhir)</b>\n"]
        for i, entry in enumerate(history, 1):
            ts = datetime.fromtimestamp(entry.executed_at).strftime("%d/%m %H:%M")
            icon = "✅" if entry.exit_code == 0 else "❌"
            lines.append(
                f"{i:2}. {icon} <code>{escape_html(entry.command[:60])}</code>"
                f"\n     <i>{ts} · exit {entry.exit_code}</i>"
            )

        from guardian.plugins.terminal.keyboard import build_terminal_keyboard
        await ctx.respond("\n".join(lines), keyboard=build_terminal_keyboard())

    async def handle_terminal_menu(self, ctx: CommandContext) -> None:
        """Tampilkan menu / info terminal."""
        from guardian.plugins.terminal.service import TerminalService

        service = TerminalService(ctx.app_ctx)
        session = await service.get_or_create_session(ctx.user.telegram_id)

        settings = ctx.app_ctx.settings
        danger_guard = getattr(settings, "terminal_danger_guard", True)
        timeout = getattr(settings, "terminal_command_timeout", 30.0)
        max_kb = getattr(settings, "terminal_max_output_kb", 10)
        enabled = getattr(settings, "terminal_enabled", True)

        text = (
            "🖥️ <b>Terminal — Full Shell Access</b>\n\n"
            f"📂 <b>CWD:</b> <code>{escape_html(session.cwd)}</code>\n\n"
            "<b>Cara Pakai:</b>\n"
            "<code>/run &lt;perintah&gt;</code> — Eksekusi perintah Linux\n"
            "<code>$ &lt;perintah&gt;</code>    — Shortcut dollar sign\n"
            "<code>/history</code>             — Riwayat perintah\n\n"
            "<b>Contoh:</b>\n"
            "<code>/run ls -la /var/log</code>\n"
            "<code>/run docker ps</code>\n"
            "<code>/run systemctl status nginx</code>\n"
            "<code>$ df -h</code>\n"
            "<code>$ ps aux | head -20</code>\n\n"
            "<b>Konfigurasi Aktif:</b>\n"
            f"• Status:      <code>{'AKTIF' if enabled else 'NONAKTIF'}</code>\n"
            f"• Danger Guard: <code>{'ON 🛡️' if danger_guard else 'OFF ⚠️'}</code>\n"
            f"• Timeout:     <code>{timeout}s</code>\n"
            f"• Max Output:  <code>{max_kb} KB</code>\n"
        )

        from guardian.plugins.terminal.keyboard import build_terminal_keyboard
        await ctx.respond(text, keyboard=build_terminal_keyboard())

    async def handle_session_reset(self, ctx: CommandContext) -> None:
        """Reset sesi terminal user ke direktori awal."""
        from guardian.plugins.terminal.service import TerminalService

        service = TerminalService(ctx.app_ctx)
        await service.reset_session(ctx.user.telegram_id)

        await ctx.respond(
            "🔄 <b>Sesi Terminal Direset</b>\n\n"
            f"📂 Working directory kembali ke: <code>/</code>"
        )

    async def handle_history_clear(self, ctx: CommandContext) -> None:
        """Hapus semua riwayat perintah terminal user."""
        from guardian.plugins.terminal.repository import TerminalRepository

        repo = TerminalRepository(ctx.app_ctx.database)
        count = await repo.clear_history(ctx.user.telegram_id)

        await ctx.respond(f"🧹 <b>Riwayat Dihapus</b>\n\n{count} perintah berhasil dihapus.")

    async def handle_callback(self, ctx: object) -> None:
        """Handle callback tombol terminal."""
        from guardian.core.bot_gateway import CallbackContext, CommandContext as CmdCtx

        if not isinstance(ctx, CallbackContext):
            return

        parts = ctx.data.split(":", 2)
        action = parts[1] if len(parts) > 1 else ""

        cmd_ctx = CmdCtx(
            user=ctx.user,
            chat_id=ctx.chat_id,
            message_id=ctx.message_id,
            command=action,
            args=[],
            raw_text=f"/terminal {action}",
            update=ctx.update,
            bot_gateway=ctx.bot_gateway,
            app_ctx=ctx.app_ctx,
        )

        if action == "menu":
            await self.handle_terminal_menu(cmd_ctx)
        elif action == "history":
            await self.handle_history(cmd_ctx)
        elif action == "reset":
            await self.handle_session_reset(cmd_ctx)
        elif action == "clear_history":
            await self.handle_history_clear(cmd_ctx)
