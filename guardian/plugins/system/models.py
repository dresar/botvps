"""Models untuk plugin system — dataclass untuk metrik sistem."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SystemInfo:
    """Informasi dasar sistem."""

    hostname: str
    os_name: str
    os_version: str
    kernel_version: str
    architecture: str
    python_version: str
    uptime_seconds: int
    boot_time: datetime


@dataclass
class CpuMetrics:
    """Metrik CPU."""

    usage_percent: float
    per_core_percent: list[float]
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float
    core_count: int
    frequency_mhz: float


@dataclass
class MemoryMetrics:
    """Metrik memori (RAM dan Swap)."""

    total_bytes: int
    available_bytes: int
    used_bytes: int
    usage_percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_percent: float


@dataclass
class DiskMetrics:
    """Metrik disk untuk satu mount point."""

    mount_point: str
    device: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float


@dataclass
class NetworkMetrics:
    """Metrik jaringan untuk satu interface."""

    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int


@dataclass
class ProcessInfo:
    """Informasi satu proses."""

    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    memory_rss_bytes: int
    status: str
    create_time: datetime


@dataclass
class AllMetrics:
    """Bundle semua metrik sistem."""

    cpu: CpuMetrics
    memory: MemoryMetrics
    disks: list[DiskMetrics]
    networks: list[NetworkMetrics]
    system_info: SystemInfo
