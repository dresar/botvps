"""Handlers untuk scheduler_ui plugin & AI Cron Scheduler Engine."""

import re
import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.plugins.scheduler_ui.service import AISchedulerService
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import build_sub_dashboard_keyboard
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class SchedulerUIHandlers:
    """Handlers untuk plugin scheduler_ui & AI Scheduled Reminders."""

    def __init__(self, service: AISchedulerService | None = None) -> None:
        self.service = service

    async def handle_schedule_router(self, ctx: CommandContext) -> None:
        """Router utama untuk command /schedule dan /remind."""
        if not ctx.args:
            await self.handle_list(ctx)
            return

        sub = ctx.args[0].lower()
        args = ctx.args[1:]

        if sub in ("list", "show"):
            await self.handle_list(ctx)
        elif sub == "add":
            await self._handle_add_schedule(ctx, args)
        elif sub in ("del", "delete", "remove"):
            await self._handle_delete_schedule(ctx, args)
        elif sub == "pause":
            await self.handle_pause(ctx)
        elif sub == "resume":
            await self.handle_resume(ctx)
        else:
            await self._handle_add_schedule(ctx, ctx.args)

    async def handle_list(self, ctx: CommandContext) -> None:
        """Tampilkan semua scheduled jobs dan pengingat aktif."""
        system_jobs = ctx.app_ctx.scheduler.get_jobs()

        lines = ["📅 <b>AI Cron Scheduler & System Jobs</b>\n"]

        # 1. AI Scheduled Reminders dari SQLite
        if self.service:
            ai_tasks = await self.service.repo.get_active_tasks()
            if ai_tasks:
                lines.append("⏰ <b>Pengingat AI / User Terjadwal:</b>")
                for t in ai_tasks:
                    freq = f"{t['interval_seconds']} detik" if t.get('interval_seconds') else (t.get('cron_expression') or 'satu-kali')
                    lines.append(
                        f"• <b>ID #{t['id']}</b> [{t['task_type'].upper()} ({freq})]:\n"
                        f"  📝 <i>{escape_html(t['message'])}</i>"
                    )
                lines.append("")

        # 2. System Jobs APScheduler
        if system_jobs:
            lines.append("⚙️ <b>System Internal Background Jobs:</b>")
            for job in system_jobs:
                status = "⏸️" if job.get("is_paused") else "▶️"
                name = escape_html(job.get("name", "—"))
                next_run = job.get("next_run", "—")
                if next_run and next_run != "—":
                    next_run = next_run[:16].replace("T", " ")
                lines.append(f"{status} <code>{name}</code> — Next: <code>{next_run}</code>")

        lines.append(
            "\n<i>Gunakan:</i>\n"
            "• <code>/schedule add interval | 10m | Pesan Pengingat</code>\n"
            "• <code>/schedule add cron | 0 8 * * * | Cek VPS Pagi Hari</code>\n"
            "• <code>/schedule del [ID]</code> — Hapus pengingat"
        )
        kb = build_sub_dashboard_keyboard()
        await ctx.respond("\n".join(lines), keyboard=kb)

    async def _handle_add_schedule(self, ctx: CommandContext, args: list[str]) -> None:
        """Tambah jadwal baru. Format: /schedule add <interval|cron|oneshot> | <waktu/sec> | <pesan>"""
        if not self.service:
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ AISchedulerService belum siap.")
            return

        raw_input = " ".join(args).strip()
        parts = [p.strip() for p in raw_input.split("|") if p.strip()]

        if len(parts) < 2:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "❌ <b>Format Tambah Jadwal Salah.</b>\n\n"
                "Gunakan format:\n"
                "<code>/schedule add interval | 10m | Pesan Pengingat</code>\n"
                "<code>/schedule add cron | 0 8 * * * | Pesan Pengingat Pagi Hari</code>\n\n"
                "<i>Atau suruh AI secara alami: /ask ingatkan aku tiap jam 8 pagi untuk cek VPS</i>",
            )
            return

        task_type_raw = parts[0].lower()
        time_part = parts[1]
        message = parts[2] if len(parts) > 2 else parts[1]

        task_type = "interval"
        interval_seconds = 600
        cron_expression = None

        if "cron" in task_type_raw:
            task_type = "cron"
            cron_expression = time_part
        else:
            task_type = "interval"
            # Parse waktu 10m, 1h, 30s, 30
            if time_part.endswith("m"):
                interval_seconds = int(time_part[:-1]) * 60
            elif time_part.endswith("h"):
                interval_seconds = int(time_part[:-1]) * 3600
            elif time_part.endswith("s"):
                interval_seconds = int(time_part[:-1])
            elif time_part.isdigit():
                interval_seconds = int(time_part)

        t = await self.service.add_schedule(
            telegram_id=ctx.user.telegram_id,
            task_type=task_type,
            message=message,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
        )

        msg = (
            f"⏰ <b>Jadwal AI Reminders Berhasil Dibuat!</b>\n\n"
            f"<b>ID Jadwal:</b> <code>#{t['id']}</code>\n"
            f"<b>Tipe:</b> <code>{t['task_type'].upper()}</code>\n"
            f"<b>Waktu/Frekuensi:</b> <code>{time_part}</code>\n"
            f"<b>Pesan:</b> <i>{escape_html(t['message'])}</i>\n\n"
            f"<i>Notifikasi Telegram akan otomatis dikirim sesuai waktu jadwal!</i>"
        )
        kb = build_sub_dashboard_keyboard()
        await ctx.respond(msg, keyboard=kb)

    async def _handle_delete_schedule(self, ctx: CommandContext, args: list[str]) -> None:
        """Hapus jadwal pengingat dari SQLite & APScheduler."""
        if not self.service or not args or not args[0].isdigit():
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Format: <code>/schedule del [ID_Jadwal]</code>"
            )
            return

        task_id = int(args[0])
        ok = await self.service.repo.delete_task(task_id)
        if ok:
            try:
                ctx.app_ctx.scheduler.remove_job(f"ai_schedule_task_{task_id}")
            except Exception:
                pass
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"🗑️ Jadwal pengingat <b>#{task_id}</b> berhasil dihapus."
            )
        else:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Jadwal pengingat <b>#{task_id}</b> tidak ditemukan."
            )

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
