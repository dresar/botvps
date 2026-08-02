"""ServiceManagerService — manajemen layanan systemd."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from guardian.core.exceptions import (
    CommandExecutionError,
    ServiceNotFoundError,
    ServiceOperationError,
)
from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.service_manager.models import ServiceInfo, ServiceListItem
from guardian.utils.sandbox import run_command

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)

ALLOWED_ACTIONS = frozenset({"start", "stop", "restart", "reload", "status"})


class ServiceManagerService(BaseService):
    """Service untuk mengelola layanan systemd.

    Menggunakan systemctl melalui SubprocessSandbox.
    TIDAK pernah menggunakan shell=True.

    Args:
        ctx: ApplicationContext.
    """

    async def list_services(
        self, unit_type: str = "service", state: str = "all"
    ) -> list[ServiceListItem]:
        """Daftar layanan systemd.

        Args:
            unit_type: Tipe unit (service, socket, timer).
            state: Filter state (all, running, failed).

        Returns:
            List ServiceListItem.
        """
        cmd = [
            "systemctl", "list-units",
            f"--type={unit_type}",
            "--no-pager",
            "--no-legend",
            "--plain",
        ]
        if state != "all":
            cmd.append(f"--state={state}")

        result = await run_command(cmd)
        if not result.success:
            raise ServiceOperationError(
                f"Gagal mendapatkan daftar layanan.", detail=result.stderr
            )

        services = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                load_state = parts[1]
                active_state = parts[2]
                sub_state = parts[3]
                description = " ".join(parts[4:]) if len(parts) > 4 else ""
                services.append(ServiceListItem(
                    name=name,
                    active_state=active_state,
                    sub_state=sub_state,
                    description=description,
                ))

        return services

    async def get_service_status(self, service_name: str) -> ServiceInfo:
        """Dapatkan status detail layanan.

        Args:
            service_name: Nama layanan systemd.

        Returns:
            ServiceInfo dengan informasi lengkap.

        Raises:
            ServiceNotFoundError: Jika layanan tidak ditemukan.
        """
        result = await run_command([
            "systemctl", "show", service_name,
            "--no-pager",
            "--property=LoadState,ActiveState,SubState,Description,MainPID,MemoryCurrent,ActiveEnterTimestamp",
        ])

        if not result.success or not result.stdout.strip():
            raise ServiceNotFoundError(f"Layanan '{service_name}' tidak ditemukan.")

        props: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                props[key.strip()] = value.strip()

        if props.get("LoadState") == "not-found":
            raise ServiceNotFoundError(f"Layanan '{service_name}' tidak ditemukan.")

        main_pid = None
        pid_str = props.get("MainPID", "0")
        if pid_str.isdigit() and int(pid_str) > 0:
            main_pid = int(pid_str)

        memory_bytes = None
        mem_str = props.get("MemoryCurrent", "")
        if mem_str.isdigit():
            memory_bytes = int(mem_str)

        since = None
        since_str = props.get("ActiveEnterTimestamp", "")
        if since_str and since_str != "n/a":
            try:
                since = datetime.fromisoformat(since_str.replace(" UTC", ""))
            except ValueError:
                pass

        return ServiceInfo(
            name=service_name,
            load_state=props.get("LoadState", "unknown"),
            active_state=props.get("ActiveState", "unknown"),
            sub_state=props.get("SubState", "unknown"),
            description=props.get("Description", ""),
            main_pid=main_pid,
            memory_bytes=memory_bytes,
            since=since,
        )

    async def control_service(self, service_name: str, action: str) -> str:
        """Jalankan operasi kontrolpada layanan.

        Args:
            service_name: Nama layanan.
            action: Aksi: start, stop, restart, reload.

        Returns:
            Output dari systemctl.

        Raises:
            ServiceOperationError: Jika operasi gagal.
        """
        if action not in ALLOWED_ACTIONS:
            raise ServiceOperationError(f"Aksi '{action}' tidak diizinkan.")

        result = await run_command([
            "systemctl", action, service_name, "--no-pager"
        ])

        if not result.success:
            raise ServiceOperationError(
                f"Gagal {action} layanan '{service_name}'.",
                detail=result.stderr or result.stdout,
            )

        return result.stdout or f"Layanan {service_name} berhasil {action}."

    async def get_journal_logs(
        self, service_name: str, lines: int = 50
    ) -> str:
        """Dapatkan log dari journald untuk layanan.

        Args:
            service_name: Nama layanan.
            lines: Jumlah baris log yang diambil.

        Returns:
            String log.
        """
        result = await run_command([
            "journalctl", "-u", service_name,
            "--no-pager", "-n", str(lines),
            "--output=short",
        ])
        return result.stdout if result.stdout else "Tidak ada log yang tersedia."

    async def health_check(self) -> ServiceHealth:
        """Cek apakah systemctl tersedia."""
        result = await run_command(["systemctl", "--version"])
        if result.success:
            return ServiceHealth(
                service_name="ServiceManagerService",
                status="healthy",
                message="systemctl tersedia.",
                checked_at=datetime.utcnow(),
            )
        return ServiceHealth(
            service_name="ServiceManagerService",
            status="unavailable",
            message="systemctl tidak tersedia (bukan Linux systemd).",
            checked_at=datetime.utcnow(),
        )
