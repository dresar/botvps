"""Service untuk AI Cron Scheduler Engine & Reminders."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.scheduler_ui.repository import AISchedulerRepository

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class AISchedulerService(BaseService):
    """Service pengelola jadwal & pengingat otomatis APScheduler."""

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self.repo = AISchedulerRepository(ctx.database)

    async def register_tasks_to_engine(self) -> None:
        """Daftarkan seluruh jadwal aktif dari SQLite ke SchedulerEngine saat startup."""
        try:
            tasks = await self.repo.get_active_tasks()
            for t in tasks:
                self.schedule_task_in_apscheduler(t)
            logger.info("Jadwal AI & Reminders berhasil didaftarkan ke engine.", count=len(tasks))
        except Exception as e:
            logger.exception("Gagal mendaftarkan jadwal ke engine.", error=str(e))

    def schedule_task_in_apscheduler(self, task_data: dict[str, Any]) -> None:
        """Tambahkan job ke APScheduler Engine."""
        task_id = task_data["id"]
        job_id = f"ai_schedule_task_{task_id}"

        async def _execute_reminder():
            logger.info("Executing scheduled reminder job...", task_id=task_id, message=task_data["message"])
            try:
                msg = (
                    f"⏰ <b>PENGINGAT TERJADWAL (AI REMINDER)</b>\n\n"
                    f"📝 <b>Pesan:</b> <i>{task_data['message']}</i>\n"
                    f"⏱️ <b>Tipe Jadwal:</b> <code>{task_data['task_type'].upper()}</code>\n"
                    f"🕒 <b>Waktu Eksekusi:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                )
                await self._ctx.bot.send_message(task_data["telegram_id"], msg)
                is_one_shot = task_data["task_type"] == "one_shot"
                await self.repo.update_last_run(task_id, deactivate_one_shot=is_one_shot)
            except Exception as e:
                logger.error("Gagal mengeksekusi pengingat terjadwal.", task_id=task_id, error=str(e))

        if task_data["task_type"] == "interval" and task_data.get("interval_seconds"):
            self._ctx.scheduler.add_interval_job(
                job_id=job_id,
                func=_execute_reminder,
                seconds=int(task_data["interval_seconds"]),
            )
        elif task_data["task_type"] == "cron" and task_data.get("cron_expression"):
            parts = task_data["cron_expression"].split()
            if len(parts) == 5:
                self._ctx.scheduler.add_cron_job(
                    job_id=job_id,
                    func=_execute_reminder,
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
        elif task_data["task_type"] == "one_shot":
            # interval default 60s fallback jika date tidak diformat
            self._ctx.scheduler.add_interval_job(
                job_id=job_id,
                func=_execute_reminder,
                seconds=int(task_data.get("interval_seconds") or 60),
            )

    async def add_schedule(
        self,
        telegram_id: int,
        task_type: str,
        message: str,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        run_at: str | None = None,
    ) -> dict[str, Any]:
        """Tambah jadwal baru ke SQLite & APScheduler."""
        t = await self.repo.add_task(
            telegram_id=telegram_id,
            task_type=task_type,
            message=message,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            run_at=run_at,
        )
        self.schedule_task_in_apscheduler(t)
        return t

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan AISchedulerService."""
        tasks = await self.repo.get_active_tasks()
        return ServiceHealth(
            service_name="AISchedulerService",
            status="healthy",
            message=f"{len(tasks)} jadwal pengingat aktif.",
            checked_at=datetime.utcnow(),
        )
