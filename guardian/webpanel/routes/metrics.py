"""Route /api/metrics — CPU, RAM, Disk, Network real-time."""

import time

import psutil
import structlog
from fastapi import APIRouter, Request

from guardian.webpanel.models import DiskInfo, ProcessInfo, SystemMetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
logger = structlog.get_logger(__name__)


@router.get("", response_model=SystemMetricsResponse)
async def get_metrics(request: Request) -> SystemMetricsResponse:
    """Ambil semua metrik sistem secara real-time."""
    cpu = psutil.cpu_percent(interval=0.5)
    cpu_freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    load = psutil.getloadavg()
    boot_time = psutil.boot_time()

    # Disk root
    disk = psutil.disk_usage("/")

    import socket
    import platform

    return SystemMetricsResponse(
        cpu_percent=cpu,
        cpu_cores=psutil.cpu_count(logical=True) or 1,
        cpu_freq_mhz=cpu_freq.current if cpu_freq else 0.0,
        ram_used_bytes=mem.used,
        ram_total_bytes=mem.total,
        ram_percent=mem.percent,
        swap_used_bytes=swap.used,
        swap_total_bytes=swap.total,
        swap_percent=swap.percent,
        disk_used_bytes=disk.used,
        disk_total_bytes=disk.total,
        disk_percent=disk.percent,
        load_avg_1m=load[0],
        load_avg_5m=load[1],
        load_avg_15m=load[2],
        uptime_seconds=int(time.time() - boot_time),
        hostname=socket.gethostname(),
        os_name=platform.system() + " " + platform.release(),
    )


@router.get("/disks", response_model=list[DiskInfo])
async def get_disks(request: Request) -> list[DiskInfo]:
    """Ambil info semua partisi disk."""
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append(DiskInfo(
                mount_point=part.mountpoint,
                filesystem=part.fstype,
                used_bytes=usage.used,
                total_bytes=usage.total,
                percent=usage.percent,
            ))
        except PermissionError:
            continue
    return disks


@router.get("/processes", response_model=list[ProcessInfo])
async def get_processes(request: Request, limit: int = 20) -> list[ProcessInfo]:
    """Ambil daftar proses dengan CPU tertinggi."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "cmdline"]):
        try:
            info = p.info
            cmd = " ".join(info.get("cmdline") or []) or info.get("name", "N/A")
            procs.append(ProcessInfo(
                pid=info["pid"],
                name=info.get("name") or "unknown",
                username=info.get("username") or "root",
                cpu_percent=info.get("cpu_percent") or 0.0,
                memory_percent=info.get("memory_percent") or 0.0,
                cmdline=cmd[:100],
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x.cpu_percent, reverse=True)
    return procs[:limit]
