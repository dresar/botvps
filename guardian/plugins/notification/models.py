"""Models untuk plugin notification/alert."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AlertConfig:
    """Konfigurasi satu alert threshold."""

    id: int
    metric_name: str
    threshold_value: float
    threshold_unit: str
    comparison_op: str
    cooldown_minutes: int
    is_active: bool
    created_by: int | None
    last_triggered_at: datetime | None
    trigger_count: int


@dataclass
class AlertTrigger:
    """Representasi alert yang dipicu."""

    alert_config: AlertConfig
    current_value: float
    triggered_at: datetime
    hostname: str
