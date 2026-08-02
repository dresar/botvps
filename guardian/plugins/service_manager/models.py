"""Models untuk plugin service_manager."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ServiceInfo:
    """Informasi layanan systemd."""

    name: str
    load_state: str       # loaded, not-found, error
    active_state: str     # active, inactive, failed, activating
    sub_state: str        # running, dead, exited, ...
    description: str
    main_pid: int | None
    memory_bytes: int | None
    since: datetime | None


@dataclass
class ServiceListItem:
    """Item ringkas untuk daftar layanan."""

    name: str
    active_state: str
    sub_state: str
    description: str
