"""Handlers untuk audit_viewer plugin."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import nav_row
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)

RESULT_EMOJI = {
    "success": "✅",
    "failed": "❌",
    "denied": "🚫",
    "pending": "⏳",
}


class AuditViewerHandlers:
    """Handlers untuk plugin audit_viewer."""

    async def handle_list(self, ctx: CommandContext) -> None:
        """Tampilkan audit log terbaru."""
        from guardian.plugins.user_manager.repository import AuditLogRepository
        repo = AuditLogRepository(ctx.app_ctx.database)
        logs = await repo.find_recent(limit=15)

        if not logs:
            await ctx.bot_gateway.send_message(ctx.chat_id, "ℹ️ Belum ada audit log.")
            return

        lines = ["📋 <b>Audit Log Terbaru</b>\n"]
        for log in logs:
            emoji = RESULT_EMOJI.get(log.get("result_status", "pending"), "❓")
            action = escape_html(log.get("action", "—"))
            name = escape_html(log.get("full_name") or f"ID:{log.get('telegram_id', '?')}")
            created = log.get("created_at", "")[:16].replace("T", " ")
            lines.append(f"{emoji} <code>{created}</code>  {name}\n   ↳ {action}")

        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)

    async def handle_user(self, ctx: CommandContext) -> None:
        """Tampilkan audit log untuk user tertentu. Syntax: /audit user [telegram_id]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/audit user [telegram_id]</code>"
            )
            return

        try:
            telegram_id = int(ctx.args[0])
        except ValueError:
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Telegram ID tidak valid.")
            return

        from guardian.plugins.user_manager.repository import AuditLogRepository, UserRepository
        audit_repo = AuditLogRepository(ctx.app_ctx.database)
        user_repo = UserRepository(ctx.app_ctx.database)

        user = await user_repo.find_by_telegram_id(telegram_id)
        if not user:
            await ctx.bot_gateway.send_message(ctx.chat_id, f"❌ User {telegram_id} tidak ditemukan.")
            return

        logs = await audit_repo.find_by_user(user.id, limit=15)
        if not logs:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"ℹ️ Tidak ada audit log untuk {escape_html(user.full_name)}."
            )
            return

        lines = [f"📋 <b>Audit Log: {escape_html(user.full_name)}</b>\n"]
        for log in logs:
            emoji = RESULT_EMOJI.get(log.get("result_status", "pending"), "❓")
            action = escape_html(log.get("action", "—"))
            created = log.get("created_at", "")[:16].replace("T", " ")
            lines.append(f"{emoji} <code>{created}</code>  {action}")

        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)
