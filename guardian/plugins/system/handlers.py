"""Handlers untuk plugin system."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.utils.formatters import (
    escape_html,
    format_bytes,
    format_load_average,
    format_uptime,
    make_progress_bar,
)
from guardian.utils.keyboard_builder import (
    build_confirmation_keyboard,
    build_system_status_keyboard,
    nav_row,
)
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class SystemHandlers:
    """Command handlers untuk plugin system."""

    def __init__(self) -> None:
        self._service: object = None

    def _get_service(self, ctx: CommandContext) -> object:
        """Lazy-load SystemService."""
        if self._service is None:
            from guardian.plugins.system.service import SystemService
            self._service = SystemService(ctx.app_ctx)
        return self._service

    async def handle_status(self, ctx: CommandContext) -> None:
        """Tampilkan dashboard status server lengkap."""
        from guardian.plugins.system.service import SystemService
        service = SystemService(ctx.app_ctx)

        loading_msg = await ctx.bot_gateway.send_message(
            ctx.chat_id, "⏳ Mengambil data sistem..."
        )

        try:
            metrics = await service.get_all_metrics()
            sysinfo = metrics.system_info
            cpu = metrics.cpu
            mem = metrics.memory
            disks = metrics.disks

            root_disk = next(
                (d for d in disks if d.mount_point == "/"), disks[0] if disks else None
            )

            cpu_bar = make_progress_bar(cpu.usage_percent)
            ram_bar = make_progress_bar(mem.usage_percent)

            text = (
                f"🤖 <b>Serverinka Guardian</b>\n"
                f"🖥️ <code>{escape_html(sysinfo.hostname)}</code>\n"
                f"🐧 {escape_html(sysinfo.os_name)} {escape_html(sysinfo.kernel_version)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⏱️ <b>Uptime:</b> {format_uptime(sysinfo.uptime_seconds)}\n\n"
                f"<b>CPU</b>  <code>{cpu_bar}</code>  {cpu.usage_percent:.1f}%  ({cpu.core_count} core)\n"
                f"<b>RAM</b>  <code>{ram_bar}</code>  {mem.usage_percent:.1f}%  "
                f"({format_bytes(mem.used_bytes)}/{format_bytes(mem.total_bytes)})\n"
            )

            if root_disk:
                disk_bar = make_progress_bar(root_disk.usage_percent)
                text += (
                    f"<b>Disk</b> <code>{disk_bar}</code>  {root_disk.usage_percent:.1f}%  "
                    f"({format_bytes(root_disk.used_bytes)}/{format_bytes(root_disk.total_bytes)})\n"
                )

            text += f"<b>Load</b> <code>{format_load_average(cpu.load_average_1m, cpu.load_average_5m, cpu.load_average_15m)}</code>"

            keyboard = build_system_status_keyboard()

            if loading_msg:
                await ctx.bot_gateway.edit_message(
                    chat_id=ctx.chat_id,
                    message_id=loading_msg.message_id,
                    text=text,
                    keyboard=keyboard,
                )
            else:
                await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=keyboard)

        except Exception as e:
            logger.exception("Gagal mengambil status sistem.", error=str(e))
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Gagal mengambil status sistem. Coba lagi nanti."
            )

    async def handle_cpu(self, ctx: CommandContext) -> None:
        """Tampilkan detail penggunaan CPU."""
        from guardian.plugins.system.service import SystemService
        service = SystemService(ctx.app_ctx)
        cpu = await service.get_cpu_metrics()

        cores_text = " | ".join(f"{p:.0f}%" for p in cpu.per_core_percent[:8])
        text = (
            f"🖥️ <b>CPU Detail</b>\n\n"
            f"Total:  {cpu.usage_percent:.1f}%\n"
            f"Core:   {cpu.core_count}\n"
            f"Freq:   {cpu.frequency_mhz:.0f} MHz\n\n"
            f"<b>Per Core:</b>\n<code>{cores_text}</code>\n\n"
            f"<b>Load Average:</b>\n"
            f"<code>{format_load_average(cpu.load_average_1m, cpu.load_average_5m, cpu.load_average_15m)}</code>"
        )

        from telegram import InlineKeyboardMarkup
        kb = InlineKeyboardMarkup([nav_row(back_data="system:status")])
        await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=kb)

    async def handle_ram(self, ctx: CommandContext) -> None:
        """Tampilkan detail penggunaan RAM."""
        from guardian.plugins.system.service import SystemService
        service = SystemService(ctx.app_ctx)
        mem = await service.get_memory_metrics()

        ram_bar = make_progress_bar(mem.usage_percent)
        swap_bar = make_progress_bar(mem.swap_percent)

        text = (
            f"💾 <b>RAM Detail</b>\n\n"
            f"Total:     {format_bytes(mem.total_bytes)}\n"
            f"Digunakan: {format_bytes(mem.used_bytes)}\n"
            f"Tersedia:  {format_bytes(mem.available_bytes)}\n"
            f"Usage:     <code>{ram_bar}</code> {mem.usage_percent:.1f}%\n\n"
            f"<b>Swap:</b>\n"
            f"Total: {format_bytes(mem.swap_total_bytes)}\n"
            f"Pakai: {format_bytes(mem.swap_used_bytes)}\n"
            f"Usage: <code>{swap_bar}</code> {mem.swap_percent:.1f}%"
        )

        kb = InlineKeyboardMarkup([nav_row(back_data="system:status")])
        await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=kb)

    async def handle_disk(self, ctx: CommandContext) -> None:
        """Tampilkan detail penggunaan disk semua partisi."""
        from guardian.plugins.system.service import SystemService
        service = SystemService(ctx.app_ctx)
        disks = await service.get_disk_metrics()

        if not disks:
            await ctx.bot_gateway.send_message(ctx.chat_id, "ℹ️ Tidak ada partisi disk yang ditemukan.")
            return

        lines = ["💿 <b>Disk Detail</b>\n"]
        for d in disks:
            bar = make_progress_bar(d.usage_percent)
            lines.append(
                f"<b>{escape_html(d.mount_point)}</b> ({d.filesystem})\n"
                f"<code>{bar}</code> {d.usage_percent:.1f}%\n"
                f"{format_bytes(d.used_bytes)} / {format_bytes(d.total_bytes)}\n"
            )

        kb = InlineKeyboardMarkup([nav_row(back_data="system:status")])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)

    async def handle_net(self, ctx: CommandContext) -> None:
        """Tampilkan statistik jaringan."""
        from guardian.plugins.system.service import SystemService
        service = SystemService(ctx.app_ctx)
        nets = await service.get_network_metrics()

        if not nets:
            await ctx.bot_gateway.send_message(ctx.chat_id, "ℹ️ Tidak ada interface jaringan aktif.")
            return

        lines = ["🌐 <b>Jaringan</b>\n"]
        for n in nets:
            lines.append(
                f"<b>{escape_html(n.interface)}</b>\n"
                f"  ↑ Sent: {format_bytes(n.bytes_sent)}\n"
                f"  ↓ Recv: {format_bytes(n.bytes_recv)}\n"
            )

        kb = InlineKeyboardMarkup([nav_row(back_data="system:status")])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)

    async def handle_proc(self, ctx: CommandContext) -> None:
        """Tampilkan proses dengan CPU tertinggi."""
        from guardian.plugins.system.service import SystemService
        service = SystemService(ctx.app_ctx)
        procs = await service.get_top_processes(limit=10)

        lines = ["⚡ <b>Top 10 Proses (CPU)</b>\n"]
        for i, p in enumerate(procs, 1):
            lines.append(
                f"{i:2}. <code>{escape_html(p.name[:20]):<20}</code>  "
                f"CPU: {p.cpu_percent:5.1f}%  RAM: {p.memory_percent:4.1f}%  "
                f"PID: {p.pid}"
            )

        kb = InlineKeyboardMarkup([nav_row(back_data="system:status")])
        await ctx.bot_gateway.send_message(
            ctx.chat_id, "\n".join(lines), keyboard=kb
        )

    async def handle_reboot_confirm(self, ctx: CommandContext) -> None:
        """Tampilkan konfirmasi reboot."""
        from guardian.utils.message_builder import build_confirmation_message
        text = build_confirmation_message(
            action="Reboot Server",
            description="Server akan reboot. Semua layanan akan terhenti sementara.",
            warning="Bot tidak akan merespons selama proses reboot (~1-5 menit).",
        )
        keyboard = build_confirmation_keyboard(
            yes_data="system:confirm_reboot_final",
            no_data="system:status",
        )
        await ctx.bot_gateway.send_message(ctx.chat_id, text, keyboard=keyboard)

    async def handle_reboot_callback(self, ctx: object) -> None:
        """Handle callback untuk navigasi system."""
        from guardian.core.bot_gateway import CallbackContext
        if not isinstance(ctx, CallbackContext):
            return

        parts = ctx.data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        from guardian.core.bot_gateway import CommandContext as CmdCtx
        cmd_ctx = CmdCtx(
            user=ctx.user,
            chat_id=ctx.chat_id,
            message_id=ctx.message_id,
            command=action,
            args=[],
            raw_text="",
            update=ctx.update,
            bot_gateway=ctx.bot_gateway,
            app_ctx=ctx.app_ctx,
        )

        if action == "status":
            await self.handle_status(cmd_ctx)
        elif action == "cpu":
            await self.handle_cpu(cmd_ctx)
        elif action == "ram":
            await self.handle_ram(cmd_ctx)
        elif action == "disk":
            await self.handle_disk(cmd_ctx)
        elif action == "net":
            await self.handle_net(cmd_ctx)
        elif action == "proc":
            await self.handle_proc(cmd_ctx)
        elif action == "confirm_reboot":
            await self.handle_reboot_confirm(cmd_ctx)
