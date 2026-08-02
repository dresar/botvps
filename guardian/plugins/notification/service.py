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

            # Pemeriksaan Peringatan Otomatis Kesehatan VPS (RAM, Disk, CPU, Failed Services)
            await self._check_vps_health_warnings(current_values, hostname)

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

    async def _check_vps_health_warnings(
        self, current_values: dict[str, float], hostname: str
    ) -> None:
        """Pemeriksaan otomatis peringatan kesehatan VPS (RAM, Disk, CPU, Failed Services)."""
        settings = self._ctx.settings
        recipient_ids = await self._ctx.auth.get_all_alert_recipient_ids()
        if not recipient_ids:
            return

        now = datetime.utcnow()
        if not hasattr(self, "_last_warning_times"):
            self._last_warning_times: dict[str, datetime] = {}

        cooldown = timedelta(minutes=15)

        # 1. RAM Warning (> alert_ram_threshold %)
        ram_val = current_values.get("ram_percent", 0.0)
        if ram_val > settings.alert_ram_threshold:
            if "ram" not in self._last_warning_times or now - self._last_warning_times["ram"] > cooldown:
                self._last_warning_times["ram"] = now
                msg = (
                    f"🚨 <b>PERINGATAN KESEHATAN VPS — RAM TINGGI</b>\n\n"
                    f"🖥️ Server: <code>{hostname}</code>\n"
                    f"⚠️ RAM Usage: <b>{ram_val:.1f}%</b> (Batas: {settings.alert_ram_threshold}%)\n\n"
                    f"<i>Saran: Periksa proses yang mengonsumsi memori besar dengan menu CPU Guard atau /cpu.</i>"
                )
                await self._ctx.bot.broadcast(recipient_ids, msg)

        # 2. Disk Warning (> alert_disk_threshold %)
        disk_val = current_values.get("disk_percent", 0.0)
        if disk_val > settings.alert_disk_threshold:
            if "disk" not in self._last_warning_times or now - self._last_warning_times["disk"] > cooldown:
                self._last_warning_times["disk"] = now
                msg = (
                    f"💾 <b>PERINGATAN KESEHATAN VPS — DISK PENUH</b>\n\n"
                    f"🖥️ Server: <code>{hostname}</code>\n"
                    f"⚠️ Disk Usage: <b>{disk_val:.1f}%</b> (Batas: {settings.alert_disk_threshold}%)\n\n"
                    f"<i>Saran: Bersihkan log atau file sampah VPS sebelum penyimpanan penuh!</i>"
                )
                await self._ctx.bot.broadcast(recipient_ids, msg)

        # 3. CPU Warning (> alert_cpu_threshold %)
        cpu_val = current_values.get("cpu_percent", 0.0)
        if cpu_val > settings.alert_cpu_threshold:
            if "cpu" not in self._last_warning_times or now - self._last_warning_times["cpu"] > cooldown:
                self._last_warning_times["cpu"] = now
                msg = (
                    f"🔥 <b>PERINGATAN KESEHATAN VPS — CPU SPIKE</b>\n\n"
                    f"🖥️ Server: <code>{hostname}</code>\n"
                    f"⚠️ CPU Usage: <b>{cpu_val:.1f}%</b> (Batas: {settings.alert_cpu_threshold}%)\n\n"
                    f"<i>Saran: Gunakan <code>/cpu top</code> untuk melihat proses teratas.</i>"
                )
                await self._ctx.bot.broadcast(recipient_ids, msg)

        # 4. Failed Services Check
        if settings.alert_service_check:
            if "service" not in self._last_warning_times or now - self._last_warning_times["service"] > cooldown:
                try:
                    from guardian.plugins.service_manager.service import ServiceManagerService
                    svc_mgr = ServiceManagerService(self._ctx)
                    failed_services = await svc_mgr.get_failed_services()
                    if failed_services:
                        self._last_warning_times["service"] = now
                        failed_names = ", ".join([f"<code>{s.name}</code>" for s in failed_services[:5]])
                        msg = (
                            f"⚙️ <b>PERINGATAN KESEHATAN VPS — SERVICE CRASHED/FAILED</b>\n\n"
                            f"🖥️ Server: <code>{hostname}</code>\n"
                            f"🔴 Service Bermasalah: {failed_names}\n\n"
                            f"<i>Gunakan menu /service untuk merestart service yang bermasalah.</i>"
                        )
                        await self._ctx.bot.broadcast(recipient_ids, msg)
                except Exception as e:
                    logger.debug("Gagal memeriksa failed services.", error=str(e))

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan notification service."""
        count = len(await self._repo.find_active())
        return ServiceHealth(
            service_name="NotificationService",
            status="healthy",
            message=f"{count} alert aktif.",
            checked_at=datetime.utcnow(),
        )
