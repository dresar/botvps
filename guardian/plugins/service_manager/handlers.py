"""Handlers untuk plugin service_manager."""

import structlog

from guardian.core.bot_gateway import CallbackContext, CommandContext
from guardian.core.exceptions import ServiceNotFoundError, ServiceOperationError
from guardian.utils.formatters import escape_html, format_bytes
from guardian.utils.keyboard_builder import build_service_action_keyboard, nav_row
from guardian.utils.validators import is_dangerous_service, is_valid_service_name
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)

STATE_EMOJI = {
    "active": "🟢",
    "inactive": "⚫",
    "failed": "🔴",
    "activating": "🟡",
    "deactivating": "🟡",
    "reloading": "🔵",
}


class ServiceManagerHandlers:
    """Handlers untuk plugin service_manager."""

    async def handle_list(self, ctx: CommandContext) -> None:
        """Daftar layanan yang berjalan."""
        from guardian.plugins.service_manager.service import ServiceManagerService
        service = ServiceManagerService(ctx.app_ctx)

        loading = await ctx.bot_gateway.send_message(ctx.chat_id, "⏳ Mengambil daftar layanan...")

        try:
            state = ctx.args[0] if ctx.args else "running"
            services = await service.list_services(state=state)

            if not services:
                text = "ℹ️ Tidak ada layanan yang cocok."
            else:
                lines = [f"⚙️ <b>Layanan ({state.upper()})</b> — {len(services)} total\n"]
                for s in services[:20]:
                    emoji = STATE_EMOJI.get(s.active_state, "⚪")
                    lines.append(
                        f"{emoji} <code>{escape_html(s.name):<35}</code> {s.sub_state}"
                    )
                if len(services) > 20:
                    lines.append(f"\n<i>...dan {len(services) - 20} layanan lainnya</i>")

                text = "\n".join(lines)

            kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
            if loading:
                await ctx.bot_gateway.edit_message(
                    ctx.chat_id, loading.message_id, text, keyboard=kb
                )
            else:
                await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=kb)

        except ServiceOperationError as e:
            err_text = f"❌ systemctl tidak tersedia.\n\n<i>Apakah ini sistem Linux dengan systemd?</i>"
            if loading:
                await ctx.bot_gateway.edit_message(ctx.chat_id, loading.message_id, err_text)
        except Exception as e:
            logger.exception("Gagal list layanan.", error=str(e))

    async def handle_status(self, ctx: CommandContext) -> None:
        """Status detail satu layanan. Syntax: /service status [nama]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/service status [nama_layanan]</code>"
            )
            return

        service_name = ctx.args[0]
        if not is_valid_service_name(service_name):
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Nama layanan tidak valid."
            )
            return

        from guardian.plugins.service_manager.service import ServiceManagerService
        svc = ServiceManagerService(ctx.app_ctx)

        try:
            info = await svc.get_service_status(service_name)
            emoji = STATE_EMOJI.get(info.active_state, "⚪")
            text = (
                f"⚙️ <b>{escape_html(info.name)}</b>\n\n"
                f"{emoji} Status: <b>{info.active_state}</b> ({info.sub_state})\n"
                f"Load:    {info.load_state}\n"
                f"Desc:    {escape_html(info.description)}\n"
            )
            if info.main_pid:
                text += f"PID:     <code>{info.main_pid}</code>\n"
            if info.memory_bytes:
                text += f"Memori:  {format_bytes(info.memory_bytes)}\n"
            if info.since:
                text += f"Sejak:   {info.since.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"

            keyboard = build_service_action_keyboard(service_name)
            await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=keyboard)

        except ServiceNotFoundError:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Layanan <code>{escape_html(service_name)}</code> tidak ditemukan."
            )

    async def handle_control(self, ctx: CommandContext) -> None:
        """Kontrol layanan (start/stop/restart). Syntax: /service [action] [nama]"""
        action = ctx.command
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                f"ℹ️ <b>Penggunaan:</b> <code>/service {action} [nama_layanan]</code>"
            )
            return

        service_name = ctx.args[0]

        if not is_valid_service_name(service_name):
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Nama layanan tidak valid.")
            return

        if is_dangerous_service(service_name):
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                f"🚫 Layanan <code>{escape_html(service_name)}</code> tidak dapat dimodifikasi."
            )
            return

        if not await ctx.app_ctx.auth.has_permission(ctx.user.telegram_id, "service:write"):
            from guardian.utils.message_builder import build_denied_message
            await ctx.bot_gateway.send_message(ctx.chat_id, build_denied_message())
            return

        loading = await ctx.bot_gateway.send_message(
            ctx.chat_id, f"⏳ Menjalankan <b>systemctl {action}</b> pada <code>{escape_html(service_name)}</code>..."
        )

        from guardian.plugins.service_manager.service import ServiceManagerService
        svc = ServiceManagerService(ctx.app_ctx)

        try:
            output = await svc.control_service(service_name, action)
            text = (
                f"✅ <b>{action.upper()} berhasil</b>\n\n"
                f"Layanan: <code>{escape_html(service_name)}</code>\n"
                f"<i>{escape_html(output[:200])}</i>"
            )
        except ServiceOperationError as e:
            text = (
                f"❌ <b>Gagal {action}</b>\n\n"
                f"Layanan: <code>{escape_html(service_name)}</code>\n"
                f"<i>{escape_html(e.detail or e.message)}</i>"
            )

        if loading:
            await ctx.bot_gateway.edit_message(ctx.chat_id, loading.message_id, text)
        else:
            await ctx.bot_gateway.send_message(ctx.chat_id, text)

    async def handle_log(self, ctx: CommandContext) -> None:
        """Tampilkan log layanan. Syntax: /service log [nama]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/service log [nama_layanan]</code>"
            )
            return

        service_name = ctx.args[0]
        if not is_valid_service_name(service_name):
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Nama layanan tidak valid.")
            return

        from guardian.plugins.service_manager.service import ServiceManagerService
        svc = ServiceManagerService(ctx.app_ctx)
        logs = await svc.get_journal_logs(service_name, lines=50)

        from guardian.utils.validators import sanitize_log_output
        clean_logs = sanitize_log_output(logs)

        text = f"📋 <b>Log: {escape_html(service_name)}</b>\n\n<pre>{escape_html(clean_logs[-3500:])}</pre>"

        kb = InlineKeyboardMarkup([nav_row(back_data=f"service:detail:{service_name}")])
        await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=kb)

    async def handle_callback(self, ctx: CallbackContext) -> None:
        """Handle callback untuk service actions."""
        parts = ctx.data.split(":")
        if len(parts) < 2:
            return

        action = parts[1]
        service_name = parts[2] if len(parts) > 2 else ""

        cmd_ctx = CommandContext(
            user=ctx.user,
            chat_id=ctx.chat_id,
            message_id=ctx.message_id,
            command=action,
            args=[service_name] if service_name else [],
            raw_text="",
            update=ctx.update,
            bot_gateway=ctx.bot_gateway,
            app_ctx=ctx.app_ctx,
        )

        if action == "list":
            await self.handle_list(cmd_ctx)
        elif action == "detail":
            cmd_ctx.command = "status"
            await self.handle_status(cmd_ctx)
        elif action in ("start", "stop", "restart"):
            await self.handle_control(cmd_ctx)
        elif action == "log":
            await self.handle_log(cmd_ctx)
