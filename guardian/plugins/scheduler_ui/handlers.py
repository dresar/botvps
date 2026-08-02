"""Handlers untuk scheduler_ui plugin."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import nav_row
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class SchedulerUIHandlers:
    """Handlers untuk plugin scheduler_ui."""

    async def handle_list(self, ctx: CommandContext) -> None:
        """Tampilkan semua scheduled jobs yang aktif."""
        jobs = ctx.app_ctx.scheduler.get_jobs()

        if not jobs:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "ℹ️ Tidak ada job yang terjadwal."
            )
            return

        lines = ["📅 <b>Scheduled Jobs</b>\n"]
        for job in jobs:
            status = "⏸️" if job.get("is_paused") else "▶️"
            name = escape_html(job.get("name", "—"))
            next_run = job.get("next_run", "—")
            if next_run and next_run != "—":
                next_run = next_run[:16].replace("T", " ")
            lines.append(f"{status} <code>{name}</code>\n   Next: <code>{next_run}</code>")

        kb = InlineKeyboardMarkup([nav_row(main_menu=True)])
        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines), keyboard=kb)

    async def handle_pause(self, ctx: CommandContext) -> None:
        """Pause scheduled job. Syntax: /schedule pause [job_id]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "ℹ️ <b>Penggunaan:</b> <code>/schedule pause [job_id]</code>"
            )
            return

        job_id = ctx.args[0]
        try:
            ctx.app_ctx.scheduler.pause_job(job_id)
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"⏸️ Job <code>{escape_html(job_id)}</code> di-pause."
            )
        except Exception as e:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Gagal pause job: {escape_html(str(e))}"
            )

    async def handle_resume(self, ctx: CommandContext) -> None:
        """Resume scheduled job. Syntax: /schedule resume [job_id]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "ℹ️ <b>Penggunaan:</b> <code>/schedule resume [job_id]</code>"
            )
            return

        job_id = ctx.args[0]
        try:
            ctx.app_ctx.scheduler.resume_job(job_id)
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"▶️ Job <code>{escape_html(job_id)}</code> dilanjutkan."
            )
        except Exception as e:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Gagal resume job: {escape_html(str(e))}"
            )
