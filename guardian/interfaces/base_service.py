"""Abstract class BaseService — semua service harus mewarisi class ini."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext


@dataclass
class ServiceHealth:
    """Status kesehatan sebuah service."""

    service_name: str
    status: str  # "healthy" | "degraded" | "unavailable"
    message: str
    checked_at: datetime


class BaseService(ABC):
    """Abstract class dasar untuk semua service Serverinka Guardian.

    Service adalah lapisan yang mengenkapsulasi logika bisnis dan
    interaksi dengan sistem (psutil, subprocess, docker, dll).

    Service menerima ApplicationContext sebagai dependensi melalui
    konstruktor (dependency injection).

    Args:
        ctx: ApplicationContext berisi semua komponen sistem.
    """

    def __init__(self, ctx: "ApplicationContext") -> None:
        self._ctx = ctx

    @abstractmethod
    async def health_check(self) -> ServiceHealth:
        """Kembalikan status kesehatan service.

        Returns:
            ServiceHealth dengan informasi status.
        """
