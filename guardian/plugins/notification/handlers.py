"""Handlers untuk plugin notification."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import nav_row
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)

METRIC_LABELS: dict[str, str] = {
    "cpu_percent": "CPU Usage",
    "ram_percent": "RAM Usage",
    "disk_percent": "Disk Usage (/)",
    "swap_percent": "Swap Usage",
    "load_average_1m": "Load Average (1m)",
    "network_bytes_recv": "Network Recv",
    "network_bytes_sent": "Network Sent",
}


class NotificationHandlers:
    """Handlers untuk plugin notification."""

    async def handle_list(self, ctx: CommandContext) -> None:
        """Tampilkan semua konfigurasi alert."""
        from guardian.plugins.notification.repository import AlertConfigRepository
        repo = AlertConfigRepository(ctx.app_ctx.database)
        alerts = await repo.find_all()

        if not alerts:
            await ctx.bot_gateway.send_message(ctx.chat_id, "ℹ️ Tidak ada alert yang terkonfigurasi.")
            return

        lines = ["🔔 <b>Konfigurasi Alert</b>\n"]
        for a in alerts:
            status = "✅" if a.is_active else "❌"
            label = METRIC_LABELS.get(a.metric_name, a.metric_name)
            triggered = f"  (dipicu {a.trigger_count}x)" if a.trigger_count > 0 else ""
            lines.append(
                f"{status} <b>{label}</b>: {a.comparison_op} {a.threshold_value} {a.threshold_unit}"
                f"  (cooldown: {a.cooldown_minutes}m){triggered}"
            )

        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)

    async def handle_threshold(self, ctx: CommandContext) -> None:
        """Ubah threshold alert. Syntax: /alert threshold [id] [nilai]"""
        if len(ctx.args) < 2:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/alert threshold [alert_id] [nilai_baru]</code>"
            )
            return

        try:
            alert_id = int(ctx.args[0])
            new_value = float(ctx.args[1])
        except ValueError:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format tidak valid. ID harus integer, nilai harus angka."
            )
            return

        from guardian.plugins.notification.repository import AlertConfigRepository
        repo = AlertConfigRepository(ctx.app_ctx.database)
        alert = await repo.find_by_id(alert_id)

        if not alert:
            await ctx.bot_gateway.send_message(ctx.chat_id, f"❌ Alert ID {alert_id} tidak ditemukan.")
            return

        await repo.update_threshold(alert_id, new_value)
        label = METRIC_LABELS.get(alert.metric_name, alert.metric_name)
        await ctx.bot_gateway.send_message(
            ctx.chat_id,
            f"✅ Threshold <b>{label}</b> diperbarui menjadi <code>{new_value}</code> {alert.threshold_unit}."
        )

    async def handle_toggle(self, ctx: CommandContext) -> None:
        """Aktifkan atau nonaktifkan alert. Syntax: /alert toggle [id]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/alert toggle [alert_id]</code>"
            )
            return

        try:
            alert_id = int(ctx.args[0])
        except ValueError:
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ ID harus berupa angka.")
            return

        from guardian.plugins.notification.repository import AlertConfigRepository
        repo = AlertConfigRepository(ctx.app_ctx.database)
        alert = await repo.find_by_id(alert_id)

        if not alert:
            await ctx.bot_gateway.send_message(ctx.chat_id, f"❌ Alert ID {alert_id} tidak ditemukan.")
            return

        new_state = not alert.is_active
        await repo.toggle_active(alert_id, new_state)
        state_text = "diaktifkan" if new_state else "dinonaktifkan"
        label = METRIC_LABELS.get(alert.metric_name, alert.metric_name)

        await ctx.bot_gateway.send_message(
            ctx.chat_id, f"✅ Alert <b>{label}</b> {state_text}."
        )

    async def handle_test(self, ctx: CommandContext) -> None:
        """Kirim test alert ke user saat ini."""
        import socket
        from guardian.utils.message_builder import build_alert_message

        hostname = socket.gethostname()
        test_msg = build_alert_message(
            hostname=hostname,
            metric_name="cpu_percent",
            current_value=95.5,
            threshold_value=90.0,
            unit="percent",
        )
        test_msg = "🧪 <b>TEST ALERT</b>\n\n" + test_msg
        await ctx.bot_gateway.send_message(ctx.chat_id, test_msg)
