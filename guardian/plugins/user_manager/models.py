"""Models untuk plugin user_manager."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserRecord:
    """Representasi record user dari database."""

    id: int
    telegram_id: int
    username: str | None
    full_name: str
    role: str
    is_active: bool
    is_blocked: bool
    alert_enabled: bool
    language_code: str
    notes: str | None
    added_by: int | None
    created_at: datetime
    updated_at: datetime
