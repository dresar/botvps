"""DockerService — manajemen Docker melalui docker SDK."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from guardian.core.exceptions import (
    ContainerNotFoundError,
    DockerNotAvailableError,
    DockerOperationError,
)
from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.docker.models import ContainerInfo, ContainerStats, ImageInfo

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


def _safe_import_docker() -> Any:
    """Coba import docker SDK, raise DockerNotAvailableError jika gagal."""
    try:
        import docker
        return docker
    except ImportError as e:
        raise DockerNotAvailableError("docker SDK tidak terinstall.") from e


class DockerService(BaseService):
    """Service untuk mengelola Docker kontainer.

    Menggunakan docker SDK Python dengan asyncio.to_thread untuk
    tidak memblokir event loop.

    Args:
        ctx: ApplicationContext.
    """

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self._client: Any = None

    def _get_client(self) -> Any:
        """Dapatkan Docker client, buat jika belum ada."""
        if self._client is None:
            docker = _safe_import_docker()
            try:
                self._client = docker.from_env()
                self._client.ping()
            except Exception as e:
                self._client = None
                raise DockerNotAvailableError(
                    f"Tidak dapat terhubung ke Docker daemon: {e}"
                ) from e
        return self._client

    async def list_containers(self, all_containers: bool = False) -> list[ContainerInfo]:
        """Daftar kontainer Docker.

        Args:
            all_containers: Jika True, tampilkan kontainer yang berhenti juga.

        Returns:
            List ContainerInfo.

        Raises:
            DockerNotAvailableError: Jika Docker tidak tersedia.
        """
        def _list() -> list[ContainerInfo]:
            client = self._get_client()
            containers = client.containers.list(all=all_containers)
            result = []
            for c in containers:
                ports_list = []
                for port, bindings in (c.ports or {}).items():
                    if bindings:
                        for b in bindings:
                            ports_list.append(f"{b['HostPort']}->{port}")
                    else:
                        ports_list.append(port)

                result.append(ContainerInfo(
                    container_id=c.id[:12],
                    name=c.name,
                    image=c.image.tags[0] if c.image.tags else c.image.short_id,
                    status=c.status,
                    state=c.attrs.get("State", {}).get("Status", "unknown"),
                    created_at=datetime.fromisoformat(
                        c.attrs["Created"].split(".")[0]
                    ) if c.attrs.get("Created") else None,
                    ports=", ".join(ports_list) or "—",
                    cpu_percent=None,
                    memory_bytes=None,
                    memory_limit_bytes=None,
                ))
            return result

        return await asyncio.to_thread(_list)

    async def get_container(self, name_or_id: str) -> ContainerInfo:
        """Dapatkan info satu kontainer.

        Args:
            name_or_id: Nama atau ID kontainer.

        Returns:
            ContainerInfo.

        Raises:
            ContainerNotFoundError: Jika kontainer tidak ditemukan.
        """
        def _get() -> ContainerInfo:
            client = self._get_client()
            try:
                c = client.containers.get(name_or_id)
                return ContainerInfo(
                    container_id=c.id[:12],
                    name=c.name,
                    image=c.image.tags[0] if c.image.tags else c.image.short_id,
                    status=c.status,
                    state=c.attrs.get("State", {}).get("Status", "unknown"),
                    created_at=None,
                    ports="",
                    cpu_percent=None,
                    memory_bytes=None,
                    memory_limit_bytes=None,
                )
            except Exception as e:
                raise ContainerNotFoundError(
                    f"Kontainer '{name_or_id}' tidak ditemukan."
                ) from e

        return await asyncio.to_thread(_get)

    async def control_container(self, name_or_id: str, action: str) -> None:
        """Kontrol kontainer (start/stop/restart).

        Args:
            name_or_id: Nama atau ID kontainer.
            action: start, stop, atau restart.

        Raises:
            ContainerNotFoundError: Jika kontainer tidak ditemukan.
            DockerOperationError: Jika operasi gagal.
        """
        allowed = {"start", "stop", "restart"}
        if action not in allowed:
            raise DockerOperationError(f"Aksi '{action}' tidak diizinkan.")

        def _control() -> None:
            client = self._get_client()
            try:
                c = client.containers.get(name_or_id)
                getattr(c, action)()
            except Exception as e:
                if "not found" in str(e).lower() or "no such" in str(e).lower():
                    raise ContainerNotFoundError(f"Kontainer '{name_or_id}' tidak ditemukan.") from e
                raise DockerOperationError(f"Gagal {action} kontainer: {e}") from e

        await asyncio.to_thread(_control)

    async def get_container_logs(
        self, name_or_id: str, tail: int = 100
    ) -> str:
        """Dapatkan log kontainer.

        Args:
            name_or_id: Nama atau ID kontainer.
            tail: Jumlah baris terakhir.

        Returns:
            String log.
        """
        def _logs() -> str:
            client = self._get_client()
            try:
                c = client.containers.get(name_or_id)
                logs = c.logs(tail=tail, timestamps=False)
                return logs.decode("utf-8", errors="replace") if logs else "Tidak ada log."
            except Exception as e:
                return f"Gagal mengambil log: {e}"

        return await asyncio.to_thread(_logs)

    async def list_images(self) -> list[ImageInfo]:
        """Daftar Docker image yang tersedia.

        Returns:
            List ImageInfo.
        """
        def _images() -> list[ImageInfo]:
            client = self._get_client()
            images = client.images.list()
            return [
                ImageInfo(
                    image_id=img.id[:17],
                    repo_tags=img.tags or ["<none>:<none>"],
                    size_bytes=img.attrs.get("Size", 0),
                    created_at=None,
                )
                for img in images
            ]

        return await asyncio.to_thread(_images)

    async def health_check(self) -> ServiceHealth:
        """Cek koneksi ke Docker daemon."""
        try:
            client = self._get_client()
            await asyncio.to_thread(client.ping)
            return ServiceHealth(
                service_name="DockerService",
                status="healthy",
                message="Docker daemon terhubung.",
                checked_at=datetime.utcnow(),
            )
        except DockerNotAvailableError as e:
            return ServiceHealth(
                service_name="DockerService",
                status="unavailable",
                message=str(e),
                checked_at=datetime.utcnow(),
            )
        except Exception as e:
            return ServiceHealth(
                service_name="DockerService",
                status="unhealthy",
                message=f"Docker error: {e}",
                checked_at=datetime.utcnow(),
            )
