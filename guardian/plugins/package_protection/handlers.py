"""Handlers untuk command /package_guard."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.plugins.package_protection.service import PackageProtectionService
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import nav_row
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class PackageProtectionHandlers:
    """Handlers untuk command /package_guard."""

    def __init__(self, service: PackageProtectionService) -> None:
        self.service = service

    async def handle_package_guard(self, ctx: CommandContext) -> None:
        """Command router utama /package_guard."""
        if not ctx.args:
            await self._show_status(ctx)
            return

        sub = ctx.args[0].lower()
        args = ctx.args[1:]

        if sub == "status":
            await self._show_status(ctx)
        elif sub == "enable":
            self.service.set_enabled(True)
            await ctx.bot_gateway.send_message(ctx.chat_id, "✅ <b>Package Protection Diaktifkan.</b>")
        elif sub == "disable":
            self.service.set_enabled(False)
            await ctx.bot_gateway.send_message(ctx.chat_id, "⚠️ <b>Package Protection Dinonaktifkan.</b>")
        elif sub == "scan":
            await self._run_scan(ctx)
        elif sub == "uninstall":
            await self._handle_uninstall(ctx, args)
        elif sub == "blocked":
            await self._handle_blocked(ctx, args)
        elif sub == "logs":
            await self._show_logs(ctx)
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "❌ Sub-command tidak dikenal. Gunakan: <code>/package_guard [status|enable|disable|scan|uninstall|blocked|logs]</code>",
            )

    async def _show_status(self, ctx: CommandContext) -> None:
        """Tampilkan status Package Protection."""
        blocked = await self.service.repo.get_blocked_packages()
        status_str = "🟢 <b>AKTIF</b>" if self.service.is_enabled else "🔴 <b>NONAKTIF</b>"
        blocked_str = ", ".join([f"<code>{p}</code>" for p in blocked]) or "Tidak ada."

        msg = (
            f"📦 <b>Package Protection Status</b>\n\n"
            f"<b>Status Monitoring:</b> {status_str}\n"
            f"<b>Interval Scan Otomatis:</b> <code>{self.service._ctx.settings.package_scan_interval_minutes} menit</code>\n\n"
            f"🚫 <b>Daftar Paket Terlarang:</b>\n{blocked_str}\n\n"
            f"<i>Sistem secara otomatis memonitor proses, sistem file, dan perintah instalasi dari paket terlarang.</i>"
        )
        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, msg, keyboard=kb)

    async def _run_scan(self, ctx: CommandContext) -> None:
        """Jalankan scan manual."""
        await ctx.bot_gateway.send_message(ctx.chat_id, "🔍 <b>Memulai Pemindaian Paket Terlarang...</b>")
        reports = await self.service.run_full_scan()
        if not reports:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "✅ <b>Scan Selesai:</b> VPS Bersih! Tidak ditemukan aplikasi / paket terlarang."
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"⚠️ <b>Scan Selesai:</b> Berhasil menemukan dan membersihkan {len(reports)} paket terlarang!"
            )

    async def _handle_uninstall(self, ctx: CommandContext, args: list[str]) -> None:
        """Uninstall manual paket terlarang."""
        if not args:
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Format: <code>/package_guard uninstall <package_name></code>")
            return
        pkg = args[0]
        ok, msg = await self.service.uninstall_package_manual(pkg)
        await ctx.bot_gateway.send_message(ctx.chat_id, msg)

    async def _handle_blocked(self, ctx: CommandContext, args: list[str]) -> None:
        """Kelola daftar paket terlarang."""
        if not args:
            blocked = await self.service.repo.get_blocked_packages()
            b_str = "\n".join([f"• <code>{p}</code>" for p in blocked]) or "Tidak ada."
            await ctx.bot_gateway.send_message(ctx.chat_id, f"🚫 <b>Daftar Paket Terlarang:</b>\n{b_str}")
            return

        action = args[0].lower()
        if action == "list":
            blocked = await self.service.repo.get_blocked_packages()
            b_str = "\n".join([f"• <code>{p}</code>" for p in blocked]) or "Tidak ada."
            await ctx.bot_gateway.send_message(ctx.chat_id, f"🚫 <b>Daftar Paket Terlarang:</b>\n{b_str}")
        elif action == "add" and len(args) >= 2:
            pkg = args[1].lower()
            ok = await self.service.repo.add_blocked_package(pkg, ctx.user.telegram_id)
            status_msg = f"✅ Paket <code>{escape_html(pkg)}</code> ditambahkan ke daftar terlarang." if ok else "❌ Gagal / Sudah ada."
            await ctx.bot_gateway.send_message(ctx.chat_id, status_msg)
        elif action == "remove" and len(args) >= 2:
            pkg = args[1].lower()
            ok = await self.service.repo.remove_blocked_package(pkg)
            status_msg = f"🗑️ Paket <code>{escape_html(pkg)}</code> dihapus dari daftar terlarang." if ok else "❌ Tidak ditemukan."
            await ctx.bot_gateway.send_message(ctx.chat_id, status_msg)
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/package_guard blocked [list|add <pkg>|remove <pkg>]</code>"
            )

    async def _show_logs(self, ctx: CommandContext) -> None:
        """Tampilkan log histori pembersihan paket."""
        logs = await self.service.repo.get_reports(limit=15)
        if not logs:
            await ctx.bot_gateway.send_message(ctx.chat_id, "📜 Belum ada log pembersihan paket.")
            return

        lines = ["📜 <b>Histori Log Package Protection</b>\n"]
        for r in logs:
            st = "✅" if r.status == "success" else "❌"
            lines.append(
                f"{st} <b>{escape_html(r.package_name)}</b>\n"
                f"   Binary: <code>{escape_html(r.binary_location)}</code>\n"
                f"   Waktu: <i>{r.executed_at.strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)
