"""Handlers untuk plugin docker."""

import structlog

from guardian.core.bot_gateway import CallbackContext, CommandContext
from guardian.core.exceptions import (
    ContainerNotFoundError,
    DockerNotAvailableError,
    DockerOperationError,
)
from guardian.utils.formatters import escape_html, format_bytes
from guardian.utils.keyboard_builder import (
    build_container_action_keyboard,
    nav_row,
)
from guardian.utils.validators import is_valid_container_name
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)

STATE_EMOJI = {
    "running": "🟢",
    "exited": "⚫",
    "paused": "🟡",
    "created": "🔵",
    "restarting": "🟡",
    "dead": "🔴",
}


class DockerHandlers:
    """Handlers untuk plugin docker."""

    async def handle_list(self, ctx: CommandContext) -> None:
        """Daftar semua kontainer Docker."""
        from guardian.plugins.docker.service import DockerService
        svc = DockerService(ctx.app_ctx)

        loading = await ctx.bot_gateway.send_message(ctx.chat_id, "⏳ Mengambil daftar kontainer...")

        try:
            show_all = "--all" in ctx.args or "-a" in ctx.args
            containers = await svc.list_containers(all_containers=show_all)

            if not containers:
                text = "ℹ️ Tidak ada kontainer yang ditemukan."
            else:
                lines = [f"🐳 <b>Docker Containers</b> ({len(containers)} total)\n"]
                for c in containers:
                    emoji = STATE_EMOJI.get(c.state, "⚪")
                    lines.append(
                        f"{emoji} <code>{escape_html(c.name):<30}</code>  "
                        f"{escape_html(c.status)}"
                    )
                text = "\n".join(lines)

            kb = InlineKeyboardMarkup([[
                *[],
            ]] + [nav_row(main_menu=True)])

            if loading:
                await ctx.bot_gateway.edit_message(
                    ctx.chat_id, loading.message_id, text,
                    keyboard=InlineKeyboardMarkup([nav_row(main_menu=True)])
                )
            else:
                await ctx.bot_gateway.send_message(
                    ctx.chat_id, text,
                    keyboard=InlineKeyboardMarkup([nav_row(main_menu=True)])
                )

        except DockerNotAvailableError:
            err = "❌ <b>Docker Tidak Tersedia</b>\n\nDocker daemon tidak dapat dijangkau."
            if loading:
                await ctx.bot_gateway.edit_message(ctx.chat_id, loading.message_id, err)

    async def handle_status(self, ctx: CommandContext) -> None:
        """Status detail satu kontainer."""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/docker status [nama_kontainer]</code>"
            )
            return

        container_name = ctx.args[0]
        from guardian.plugins.docker.service import DockerService
        svc = DockerService(ctx.app_ctx)

        try:
            c = await svc.get_container(container_name)
            emoji = STATE_EMOJI.get(c.state, "⚪")
            text = (
                f"🐳 <b>{escape_html(c.name)}</b>\n\n"
                f"{emoji} Status: <b>{c.status}</b>\n"
                f"Image:  {escape_html(c.image)}\n"
                f"ID:     <code>{c.container_id}</code>\n"
            )
            keyboard = build_container_action_keyboard(container_name)
            await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=keyboard)

        except ContainerNotFoundError:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                f"❌ Kontainer <code>{escape_html(container_name)}</code> tidak ditemukan."
            )

    async def handle_control(self, ctx: CommandContext) -> None:
        """Start/Stop/Restart kontainer."""
        action = ctx.command
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                f"ℹ️ <b>Penggunaan:</b> <code>/docker {action} [nama_kontainer]</code>"
            )
            return

        container_name = ctx.args[0]
        if not is_valid_container_name(container_name):
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Nama kontainer tidak valid.")
            return

        if not await ctx.app_ctx.auth.has_permission(ctx.user.telegram_id, "docker:write"):
            from guardian.utils.message_builder import build_denied_message
            await ctx.bot_gateway.send_message(ctx.chat_id, build_denied_message())
            return

        loading = await ctx.bot_gateway.send_message(
            ctx.chat_id,
            f"⏳ Menjalankan <b>docker {action}</b> pada <code>{escape_html(container_name)}</code>..."
        )

        from guardian.plugins.docker.service import DockerService
        svc = DockerService(ctx.app_ctx)

        try:
            await svc.control_container(container_name, action)
            text = (
                f"✅ <b>{action.upper()} berhasil</b>\n\n"
                f"Kontainer: <code>{escape_html(container_name)}</code>"
            )
        except ContainerNotFoundError:
            text = f"❌ Kontainer <code>{escape_html(container_name)}</code> tidak ditemukan."
        except DockerOperationError as e:
            text = f"❌ Gagal {action}: {escape_html(e.message)}"

        if loading:
            await ctx.bot_gateway.edit_message(ctx.chat_id, loading.message_id, text)
        else:
            await ctx.bot_gateway.send_message(ctx.chat_id, text)

    async def handle_log(self, ctx: CommandContext) -> None:
        """Tampilkan log kontainer."""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/docker log [nama_kontainer]</code>"
            )
            return

        container_name = ctx.args[0]
        from guardian.plugins.docker.service import DockerService
        svc = DockerService(ctx.app_ctx)

        logs = await svc.get_container_logs(container_name, tail=80)

        from guardian.utils.validators import sanitize_log_output
        clean = sanitize_log_output(logs)

        text = f"📋 <b>Log: {escape_html(container_name)}</b>\n\n<pre>{escape_html(clean[-3500:])}</pre>"
        kb = InlineKeyboardMarkup([nav_row(back_data=f"docker:detail:{container_name}")])
        await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=kb)

    async def handle_images(self, ctx: CommandContext) -> None:
        """Daftar Docker images."""
        from guardian.plugins.docker.service import DockerService
        svc = DockerService(ctx.app_ctx)

        try:
            images = await svc.list_images()
            if not images:
                await ctx.bot_gateway.send_message(ctx.chat_id, "ℹ️ Tidak ada image yang ditemukan.")
                return

            lines = [f"🖼️ <b>Docker Images</b> ({len(images)} total)\n"]
            for img in images:
                tags = ", ".join(img.repo_tags[:2])
                lines.append(f"• {escape_html(tags)} ({format_bytes(img.size_bytes)})")

            await ctx.bot_gateway.send_message(
                ctx.chat_id, "\n".join(lines),
                keyboard=InlineKeyboardMarkup([nav_row(main_menu=True)])
            )

        except DockerNotAvailableError:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Docker daemon tidak dapat dijangkau."
            )

    async def handle_callback(self, ctx: CallbackContext) -> None:
        """Handle callback untuk docker actions."""
        parts = ctx.data.split(":")
        if len(parts) < 2:
            return

        action = parts[1]
        container_name = parts[2] if len(parts) > 2 else ""

        cmd_ctx = CommandContext(
            user=ctx.user,
            chat_id=ctx.chat_id,
            message_id=ctx.message_id,
            command=action,
            args=[container_name] if container_name else [],
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
        elif action == "images":
            await self.handle_images(cmd_ctx)
