"""NotificationService — pengecekan threshold dan broadcast alert."""

import socket
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.notification.models import AlertConfig, AlertTrigger
from guardian.plugins.notification.repository import AlertConfigRepository

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)

COMPARISON_OPS = {
    "gt": lambda current, threshold: current > threshold,
    "gte": lambda current, threshold: current >= threshold,
    "lt": lambda current, threshold: current < threshold,
    "lte": lambda current, threshold: current <= threshold,
    "eq": lambda current, threshold: current == threshold,
}


class NotificationService(BaseService):
    """Service untuk pengecekan alert dan pengiriman notifikasi.

    Berjalan secara periodik via SchedulerEngine.

    Args:
        ctx: ApplicationContext.
    """

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self._repo = AlertConfigRepository(ctx.database)

    async def run_alert_check(self) -> None:
        """Jalankan satu siklus pengecekan semua alert aktif.

        Dipanggil oleh SchedulerEngine secara periodik.
        """
        try:
            alerts = await self._repo.find_active()
            if not alerts:
                return

            from guardian.plugins.system.service import SystemService
            sys_service = SystemService(self._ctx)
            cpu = await sys_service.get_cpu_metrics()
            mem = await sys_service.get_memory_metrics()
            disks = await sys_service.get_disk_metrics()

            root_disk = next((d for d in disks if d.mount_point == "/"), None)

            current_values: dict[str, float] = {
                "cpu_percent": cpu.usage_percent,
                "ram_percent": mem.usage_percent,
                "disk_percent": root_disk.usage_percent if root_disk else 0.0,
                "swap_percent": mem.swap_percent,
                "load_average_1m": cpu.load_average_1m,
            }

            hostname = socket.gethostname()

            for alert in alerts:
                current = current_values.get(alert.metric_name)
                if current is None:
                    continue

                if self._is_in_cooldown(alert):
                    continue

                op_fn = COMPARISON_OPS.get(alert.comparison_op)
                if op_fn and op_fn(current, alert.threshold_value):
                    await self._fire_alert(alert, current, hostname)

        except Exception:
            logger.exception("Error pada alert check loop.")

    def _is_in_cooldown(self, alert: AlertConfig) -> bool:
        """Cek apakah alert masih dalam periode cooldown."""
        if not alert.last_triggered_at:
            return False
        cooldown_end = alert.last_triggered_at + timedelta(minutes=alert.cooldown_minutes)
        return datetime.utcnow() < cooldown_end

    async def _fire_alert(
        self, alert: AlertConfig, current_value: float, hostname: str
    ) -> None:
        """Kirim notifikasi alert ke semua admin yang berhak."""
        await self._repo.update_triggered(alert.id)

        recipient_ids = await self._ctx.auth.get_all_alert_recipient_ids()
        if not recipient_ids:
            logger.warning("Tidak ada penerima alert.", alert_id=alert.id)
            return

        from guardian.utils.message_builder import build_alert_message
        message = build_alert_message(
            hostname=hostname,
            metric_name=alert.metric_name,
            current_value=current_value,
            threshold_value=alert.threshold_value,
            unit=alert.threshold_unit,
        )

        result = await self._ctx.bot.broadcast(recipient_ids, message)

        logger.info(
            "Alert terkirim.",
            metric=alert.metric_name,
            current=current_value,
            threshold=alert.threshold_value,
            sent=result.sent_count,
            failed=result.failed_count,
        )

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan notification service."""
        count = len(await self._repo.find_active())
        return ServiceHealth(
            service_name="NotificationService",
            status="healthy",
            message=f"{count} alert aktif.",
            checked_at=datetime.utcnow(),
        )
