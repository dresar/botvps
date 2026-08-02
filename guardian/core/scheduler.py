"""SchedulerEngine — manajemen job terjadwal menggunakan APScheduler."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Coroutine

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from guardian.core.exceptions import InvalidCronExpressionError, JobNotFoundError

if TYPE_CHECKING:
    from guardian.core.database import DatabaseManager

logger = structlog.get_logger(__name__)

JobFunc = Callable[..., Coroutine[Any, Any, None]]


class SchedulerEngine:
    """Mengelola scheduled jobs menggunakan APScheduler.

    Menyediakan API untuk plugin mendaftarkan job terjadwal.
    Job internal (alert loop, backup) juga dikelola di sini.

    Args:
        db: DatabaseManager untuk persistensi job.
    """

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._running = False

    def start(self) -> None:
        """Mulai scheduler engine."""
        if not self._running:
            self._scheduler.start()
            self._running = True
            logger.info("SchedulerEngine dimulai.")

    def stop(self) -> None:
        """Hentikan scheduler engine."""
        if self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("SchedulerEngine dihentikan.")

    def add_interval_job(
        self,
        job_id: str,
        func: JobFunc,
        seconds: int,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Tambah job dengan interval tetap.

        Args:
            job_id: ID unik job.
            func: Async function yang akan dijalankan.
            seconds: Interval dalam detik.
            args: Argumen positional.
            kwargs: Argumen keyword.
        """
        self._scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id,
            replace_existing=True,
            args=args or [],
            kwargs=kwargs or {},
        )
        logger.info("Interval job ditambahkan.", job_id=job_id, seconds=seconds)

    def add_cron_job(
        self,
        job_id: str,
        func: JobFunc,
        cron_expression: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Tambah job dengan ekspresi cron.

        Args:
            job_id: ID unik job.
            func: Async function yang akan dijalankan.
            cron_expression: Ekspresi cron 5 field (misal "0 2 * * *").
            args: Argumen positional.
            kwargs: Argumen keyword.

        Raises:
            InvalidCronExpressionError: Jika ekspresi cron tidak valid.
        """
        try:
            fields = cron_expression.strip().split()
            if len(fields) != 5:
                raise ValueError(f"Ekspresi cron harus 5 field, dapat {len(fields)}")
            minute, hour, day, month, day_of_week = fields
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone="UTC",
            )
        except Exception as e:
            raise InvalidCronExpressionError(
                f"Ekspresi cron tidak valid: '{cron_expression}'. Error: {e}"
            ) from e

        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            args=args or [],
            kwargs=kwargs or {},
        )
        logger.info("Cron job ditambahkan.", job_id=job_id, cron=cron_expression)

    def remove_job(self, job_id: str) -> None:
        """Hapus job berdasarkan ID.

        Args:
            job_id: ID job yang akan dihapus.

        Raises:
            JobNotFoundError: Jika job tidak ditemukan.
        """
        try:
            self._scheduler.remove_job(job_id)
            logger.info("Job dihapus.", job_id=job_id)
        except Exception as e:
            raise JobNotFoundError(f"Job '{job_id}' tidak ditemukan.") from e

    def pause_job(self, job_id: str) -> None:
        """Pause job berdasarkan ID."""
        try:
            self._scheduler.pause_job(job_id)
        except Exception as e:
            raise JobNotFoundError(f"Job '{job_id}' tidak ditemukan.") from e

    def resume_job(self, job_id: str) -> None:
        """Resume job yang di-pause."""
        try:
            self._scheduler.resume_job(job_id)
        except Exception as e:
            raise JobNotFoundError(f"Job '{job_id}' tidak ditemukan.") from e

    def get_jobs(self) -> list[dict[str, Any]]:
        """Dapatkan semua job yang terdaftar.

        Returns:
            List dict dengan informasi job.
        """
        result = []
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            result.append({
                "id": job.id,
                "name": job.name or job.id,
                "next_run": next_run.isoformat() if next_run else None,
                "is_paused": next_run is None,
            })
        return result

    def job_exists(self, job_id: str) -> bool:
        """Cek apakah job dengan ID tertentu ada.

        Args:
            job_id: ID job.

        Returns:
            True jika job ada.
        """
        return self._scheduler.get_job(job_id) is not None

    @property
    def is_running(self) -> bool:
        """True jika scheduler sedang berjalan."""
        return self._running
