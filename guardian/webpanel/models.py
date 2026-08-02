"""Pydantic response models untuk Web Panel API."""

from pydantic import BaseModel


class SystemMetricsResponse(BaseModel):
    cpu_percent: float
    cpu_cores: int
    cpu_freq_mhz: float
    ram_used_bytes: int
    ram_total_bytes: int
    ram_percent: float
    swap_used_bytes: int
    swap_total_bytes: int
    swap_percent: float
    disk_used_bytes: int
    disk_total_bytes: int
    disk_percent: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    uptime_seconds: int
    hostname: str
    os_name: str


class DiskInfo(BaseModel):
    mount_point: str
    filesystem: str
    used_bytes: int
    total_bytes: int
    percent: float


class ProcessInfo(BaseModel):
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    cmdline: str


class DockerContainerResponse(BaseModel):
    id: str
    name: str
    image: str
    status: str
    state: str
    ports: str
    created: str


class ServiceResponse(BaseModel):
    name: str
    description: str
    status: str
    active_state: str
    sub_state: str
    enabled: bool


class AlertResponse(BaseModel):
    id: int
    name: str
    metric: str
    threshold: float
    current_value: float | None
    is_enabled: bool
    last_triggered: float | None


class AIMessageResponse(BaseModel):
    response: str
    provider: str


class TerminalResponse(BaseModel):
    command: str
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    blocked: bool
    block_reason: str
    cwd: str


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""


class SuccessResponse(BaseModel):
    message: str
    data: dict = {}
