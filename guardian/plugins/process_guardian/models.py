"""Data models untuk process_guardian plugin."""

from datetime import datetime
from pydantic import BaseModel, Field


class ProcessInfoDTO(BaseModel):
    """DTO informasi proses Linux."""

    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    cmdline: str
    running_time: str
    create_time: float


class CPUGuardRuleDTO(BaseModel):
    """DTO aturan whitelist / blacklist CPU guard."""

    id: int | None = None
    rule_type: str  # 'whitelist' atau 'blacklist'
    value: str
    added_by: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CPUGuardHistoryDTO(BaseModel):
    """DTO histori tindakan kill / warning CPU guard."""

    id: int | None = None
    pid: int
    process_name: str
    username: str
    cpu_percent: float
    memory_percent: float
    cmdline: str
    running_time: str
    action_taken: str  # 'SIGTERM', 'SIGKILL', 'WARNING'
    status: str  # 'success', 'failed'
    reason: str
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class CPUGuardConfigDTO(BaseModel):
    """DTO status & konfigurasi CPU Guard."""

    enabled: bool
    limit_percent: float
    check_interval_seconds: int
    grace_timeout_seconds: int
    kill_mode: str
    notification_enabled: bool
    cooldown_seconds: int
    whitelist: list[str]
    blacklist: list[str]
