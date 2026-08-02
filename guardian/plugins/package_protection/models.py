"""Data models untuk package_protection plugin."""

from datetime import datetime
from pydantic import BaseModel, Field


class BlockedPackageDTO(BaseModel):
    """DTO paket terlarang."""

    id: int | None = None
    name: str
    added_by: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UninstallReportDTO(BaseModel):
    """DTO laporan pembersihan/uninstall paket terlarang."""

    id: int | None = None
    package_name: str
    install_method: str
    binary_location: str
    config_location: str
    cache_location: str
    status: str  # 'success', 'failed'
    details: str
    executed_at: datetime = Field(default_factory=datetime.utcnow)
