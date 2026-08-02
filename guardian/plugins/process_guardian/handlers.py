"""Handlers untuk command /cpu_guard."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.plugins.process_guardian.service import ProcessGuardianService
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import nav_row
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class CPUGuardHandlers:
    """Handlers untuk command /cpu_guard."""

    def __init__(self, service: ProcessGuardianService) -> None:
        self.service = service

    async def handle_cpu_guard(self, ctx: CommandContext) -> None:
        """Command router utama /cpu_guard."""
        if not ctx.args:
            await self._show_status(ctx)
            return

        sub = ctx.args[0].lower()
        args = ctx.args[1:]

        if sub == "status":
            await self._show_status(ctx)
        elif sub == "enable":
            self.service.set_enabled(True)
            await ctx.bot_gateway.send_message(ctx.chat_id, "✅ <b>Auto Process Guardian Diaktifkan.</b>")
        elif sub == "disable":
            self.service.set_enabled(False)
            await ctx.bot_gateway.send_message(ctx.chat_id, "⚠️ <b>Auto Process Guardian Dinonaktifkan.</b>")
        elif sub == "top":
            await self._show_top(ctx)
        elif sub == "kill":
            await self._handle_kill(ctx, args)
        elif sub == "whitelist":
            await self._handle_rule(ctx, "whitelist", args)
        elif sub == "blacklist":
            await self._handle_rule(ctx, "blacklist", args)
        elif sub == "history":
            await self._show_history(ctx)
        elif sub == "config":
            await self._show_config(ctx)
        elif sub == "test":
            await self._run_test(ctx)
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "❌ Sub-command tidak dikenal. Gunakan: <code>/cpu_guard [status|enable|disable|top|kill|whitelist|blacklist|history|config|test]</code>",
            )

    async def _show_status(self, ctx: CommandContext) -> None:
        """Tampilkan dashboard status CPU Guard."""
        cfg = await self.service.get_config_summary()
        today_kills = await self.service.repo.count_today_kills()
        top = await self.service.get_top_cpu_processes(limit=3)

        status_text = "🟢 <b>AKTIF</b>" if cfg.enabled else "🔴 <b>NONAKTIF</b>"
        top_str = "\n".join(
            [f"• <code>{p.name}</code> (PID {p.pid}) — <b>{p.cpu_percent:.1f}% CPU</b>" for p in top]
        ) or "Tidak ada."

        msg = (
            f"🛡️ <b>Auto Process Guardian Dashboard</b>\n\n"
            f"<b>Status Monitoring:</b> {status_text}\n"
            f"<b>Batas CPU (Threshold):</b> <code>{cfg.limit_percent}%</code>\n"
            f"<b>Mode Tindakan:</b> <code>{cfg.kill_mode.upper()}</code>\n"
            f"<b>Jumlah Kill Hari Ini:</b> <code>{today_kills}</code>\n"
            f"<b>Waktu Cooldown:</b> <code>{cfg.cooldown_seconds}s</code>\n\n"
            f"🔥 <b>Top 3 CPU Processes Saat Ini:</b>\n{top_str}\n\n"
            f"<b>Whitelist (Rule Custom):</b> {len(cfg.whitelist)} aplikasi\n"
            f"<b>Blacklist (Rule Custom):</b> {len(cfg.blacklist)} aplikasi"
        )
        from guardian.utils.keyboard_builder import build_sub_dashboard_keyboard
        from telegram import InlineKeyboardButton
        extra = [
            [
                InlineKeyboardButton("🔥 Top 20 CPU", callback_data="cpu_guard:top"),
                InlineKeyboardButton("📜 Histori Kill", callback_data="cpu_guard:history"),
            ]
        ]
        kb = build_sub_dashboard_keyboard(extra)
        await ctx.respond(msg, keyboard=kb)

    async def _show_top(self, ctx: CommandContext) -> None:
        """Tampilkan Top 20 CPU processes."""
        top = await self.service.get_top_cpu_processes(limit=20)
        lines = ["🔥 <b>Top 20 Penggunaan CPU Proses</b>\n"]
        for idx, p in enumerate(top, 1):
            lines.append(
                f"<b>{idx}. {escape_html(p.name)}</b> (PID {p.pid})\n"
                f"   CPU: <code>{p.cpu_percent:.1f}%</code> | RAM: <code>{p.memory_percent:.1f}%</code> | User: <code>{escape_html(p.username)}</code>"
            )
        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)

    async def _handle_kill(self, ctx: CommandContext, args: list[str]) -> None:
        """Kill manual proses by PID."""
        if not args or not args[0].isdigit():
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Format: <code>/cpu_guard kill <PID></code>")
            return
        pid = int(args[0])
        success, msg = await self.service.kill_process_by_pid(pid, ctx.user.telegram_id)
        await ctx.bot_gateway.send_message(ctx.chat_id, msg)

    async def _handle_rule(self, ctx: CommandContext, rule_type: str, args: list[str]) -> None:
        """Tambah atau hapus whitelist / blacklist."""
        if len(args) < 2 or args[0].lower() not in ("add", "remove"):
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Format: <code>/cpu_guard {rule_type} [add|remove] <nama_proses></code>"
            )
            return

        action = args[0].lower()
        val = args[1].lower()

        if action == "add":
            ok = await self.service.repo.add_rule(rule_type, val, ctx.user.telegram_id)
            status_msg = f"✅ <code>{escape_html(val)}</code> berhasil ditambahkan ke {rule_type}." if ok else "❌ Gagal / Sudah ada."
        else:
            ok = await self.service.repo.remove_rule(rule_type, val)
            status_msg = f"🗑️ <code>{escape_html(val)}</code> berhasil dihapus dari {rule_type}." if ok else "❌ Tidak ditemukan."

        await ctx.bot_gateway.send_message(ctx.chat_id, status_msg)

    async def _show_history(self, ctx: CommandContext) -> None:
        """Tampilkan histori tindakan kill/warn."""
        logs = await self.service.repo.get_history(limit=15)
        if not logs:
            await ctx.bot_gateway.send_message(ctx.chat_id, "📜 Belum ada histori tindakan CPU Guard.")
            return

        lines = ["📜 <b>Histori Tindakan CPU Guard (Terbaru)</b>\n"]
        for r in logs:
            st = "✅" if r.status == "success" else "❌"
            lines.append(
                f"{st} <b>{escape_html(r.process_name)}</b> (PID {r.pid})\n"
                f"   Tindakan: <code>{r.action_taken}</code> | CPU: <code>{r.cpu_percent:.1f}%</code>\n"
                f"   Waktu: <i>{r.executed_at.strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)

    async def _show_config(self, ctx: CommandContext) -> None:
        """Tampilkan konfigurasi aktif."""
        cfg = await self.service.get_config_summary()
        msg = (
            f"⚙️ <b>Konfigurasi Aktif CPU Guard</b>\n\n"
            f"• <b>Status:</b> {'Aktif' if cfg.enabled else 'Nonaktif'}\n"
            f"• <b>CPU Limit:</b> <code>{cfg.limit_percent}%</code>\n"
            f"• <b>Check Interval:</b> <code>{cfg.check_interval_seconds}s</code>\n"
            f"• <b>Grace Timeout:</b> <code>{cfg.grace_timeout_seconds}s</code>\n"
            f"• <b>Kill Mode:</b> <code>{cfg.kill_mode.upper()}</code>\n"
            f"• <b>Cooldown:</b> <code>{cfg.cooldown_seconds}s</code>\n"
            f"• <b>Notification:</b> {'Ya' if cfg.notification_enabled else 'Tidak'}\n"
        )
        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, msg, keyboard=kb)

    async def _run_test(self, ctx: CommandContext) -> None:
        """Simulasi pengujian CPU Guard tanpa membunuh proses."""
        top = await self.service.get_top_cpu_processes(limit=5)
        top_str = "\n".join([f"• <code>{p.name}</code> (PID {p.pid}) — <b>{p.cpu_percent:.1f}% CPU</b>" for p in top])
        msg = (
            f"🧪 <b>Simulasi Pengecekan CPU Guard</b>\n\n"
            f"<b>Status Monitoring:</b> Berjalan Normal\n"
            f"<b>Batas Ambang:</b> <code>{self.service._ctx.settings.cpu_usage_limit}%</code>\n\n"
            f"<b>Top 5 Proses Terdeteksi:</b>\n{top_str}\n\n"
            f"<i>Simulasi selesai. Tidak ada proses yang dihentikan saat test.</i>"
        )
        await ctx.bot_gateway.send_message(ctx.chat_id, msg)
