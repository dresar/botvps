"""SystemService — mengambil metrik sistem menggunakan psutil."""

import asyncio
import platform
import socket
import sys
from datetime import datetime
from typing import TYPE_CHECKING

import psutil
import structlog

from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.system.models import (
    AllMetrics,
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessInfo,
    SystemInfo,
)

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class SystemService(BaseService):
    """Service untuk mengambil metrik dan informasi sistem Linux.

    Menggunakan psutil untuk semua metrik. Operasi psutil yang blocking
    dijalankan di executor untuk tidak memblokir event loop.

    Args:
        ctx: ApplicationContext.
    """

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)

    async def get_system_info(self) -> SystemInfo:
        """Dapatkan informasi dasar sistem.

        Returns:
            SystemInfo dengan hostname, OS, kernel, uptime, dll.
        """
        def _get_info() -> SystemInfo:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = int((datetime.now() - boot_time).total_seconds())
            try:
                freq = psutil.cpu_freq()
                freq_mhz = freq.current if freq else 0.0
            except Exception:
                freq_mhz = 0.0

            return SystemInfo(
                hostname=socket.gethostname(),
                os_name=platform.system(),
                os_version=platform.version(),
                kernel_version=platform.release(),
                architecture=platform.machine(),
                python_version=sys.version.split()[0],
                uptime_seconds=uptime,
                boot_time=boot_time,
            )

        return await asyncio.to_thread(_get_info)

    async def get_cpu_metrics(self) -> CpuMetrics:
        """Dapatkan metrik CPU saat ini.

        Returns:
            CpuMetrics dengan usage percent dan load average.
        """
        def _get_cpu() -> CpuMetrics:
            usage = psutil.cpu_percent(interval=0.5)
            per_core = psutil.cpu_percent(interval=None, percpu=True)
            load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
            freq = psutil.cpu_freq()

            return CpuMetrics(
                usage_percent=usage,
                per_core_percent=list(per_core),
                load_average_1m=load[0],
                load_average_5m=load[1],
                load_average_15m=load[2],
                core_count=psutil.cpu_count(logical=True) or 1,
                frequency_mhz=freq.current if freq else 0.0,
            )

        return await asyncio.to_thread(_get_cpu)

    async def get_memory_metrics(self) -> MemoryMetrics:
        """Dapatkan metrik memori (RAM dan Swap).

        Returns:
            MemoryMetrics dengan total, used, available, dan swap.
        """
        def _get_mem() -> MemoryMetrics:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return MemoryMetrics(
                total_bytes=mem.total,
                available_bytes=mem.available,
                used_bytes=mem.used,
                usage_percent=mem.percent,
                swap_total_bytes=swap.total,
                swap_used_bytes=swap.used,
                swap_percent=swap.percent,
            )

        return await asyncio.to_thread(_get_mem)

    async def get_disk_metrics(self) -> list[DiskMetrics]:
        """Dapatkan metrik disk untuk semua mount point.

        Returns:
            List DiskMetrics untuk setiap partisi.
        """
        def _get_disk() -> list[DiskMetrics]:
            result = []
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    result.append(DiskMetrics(
                        mount_point=part.mountpoint,
                        device=part.device,
                        filesystem=part.fstype,
                        total_bytes=usage.total,
                        used_bytes=usage.used,
                        free_bytes=usage.free,
                        usage_percent=usage.percent,
                    ))
                except (PermissionError, OSError):
                    continue
            return result

        return await asyncio.to_thread(_get_disk)

    async def get_network_metrics(self) -> list[NetworkMetrics]:
        """Dapatkan statistik jaringan untuk semua interface.

        Returns:
            List NetworkMetrics per interface.
        """
        def _get_net() -> list[NetworkMetrics]:
            stats = psutil.net_io_counters(pernic=True)
            result = []
            for iface, counters in stats.items():
                if iface.startswith("lo"):
                    continue
                result.append(NetworkMetrics(
                    interface=iface,
                    bytes_sent=counters.bytes_sent,
                    bytes_recv=counters.bytes_recv,
                    packets_sent=counters.packets_sent,
                    packets_recv=counters.packets_recv,
                    errors_in=counters.errin,
                    errors_out=counters.errout,
                ))
            return result

        return await asyncio.to_thread(_get_net)

    async def get_top_processes(self, limit: int = 10) -> list[ProcessInfo]:
        """Dapatkan proses dengan penggunaan CPU tertinggi.

        Args:
            limit: Jumlah proses yang dikembalikan.

        Returns:
            List ProcessInfo diurutkan berdasarkan CPU usage.
        """
        def _get_procs() -> list[ProcessInfo]:
            procs = []
            for proc in psutil.process_iter(
                ["pid", "name", "username", "cpu_percent", "memory_percent",
                 "memory_info", "status", "create_time"]
            ):
                try:
                    info = proc.info
                    procs.append(ProcessInfo(
                        pid=info["pid"],
                        name=info["name"] or "unknown",
                        username=info.get("username") or "unknown",
                        cpu_percent=info["cpu_percent"] or 0.0,
                        memory_percent=info["memory_percent"] or 0.0,
                        memory_rss_bytes=info["memory_info"].rss if info.get("memory_info") else 0,
                        status=info["status"] or "unknown",
                        create_time=datetime.fromtimestamp(info["create_time"] or 0),
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return sorted(procs, key=lambda p: p.cpu_percent, reverse=True)[:limit]

        return await asyncio.to_thread(_get_procs)

    async def get_all_metrics(self) -> AllMetrics:
        """Dapatkan semua metrik sekaligus secara concurrent.

        Returns:
            AllMetrics dengan semua data sistem.
        """
        async with asyncio.TaskGroup() as tg:
            cpu_task = tg.create_task(self.get_cpu_metrics())
            mem_task = tg.create_task(self.get_memory_metrics())
            disk_task = tg.create_task(self.get_disk_metrics())
            net_task = tg.create_task(self.get_network_metrics())
            sys_task = tg.create_task(self.get_system_info())

        return AllMetrics(
            cpu=cpu_task.result(),
            memory=mem_task.result(),
            disks=disk_task.result(),
            networks=net_task.result(),
            system_info=sys_task.result(),
        )

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan SystemService."""
        try:
            await asyncio.to_thread(psutil.cpu_percent, 0)
            return ServiceHealth(
                service_name="SystemService",
                status="healthy",
                message="psutil berjalan normal.",
                checked_at=datetime.utcnow(),
            )
        except Exception as e:
            return ServiceHealth(
                service_name="SystemService",
                status="unhealthy",
                message=f"psutil error: {e}",
                checked_at=datetime.utcnow(),
            )
