"""Route /api/docker — manajemen Docker container."""

import structlog
from fastapi import APIRouter, HTTPException, Request

from guardian.webpanel.models import DockerContainerResponse, ErrorResponse, SuccessResponse

router = APIRouter(prefix="/api/docker", tags=["docker"])
logger = structlog.get_logger(__name__)


def _get_docker_client() -> "object":
    import docker
    return docker.from_env()


def _format_container(c: "object") -> DockerContainerResponse:
    ports_dict = getattr(c, "ports", {}) or {}
    ports_str = ", ".join(
        f"{v[0]['HostPort'] if v else '?'}→{k}"
        for k, v in ports_dict.items()
        if k
    ) if ports_dict else "—"
    created = str(c.attrs.get("Created", ""))[:19].replace("T", " ")
    return DockerContainerResponse(
        id=c.short_id,
        name=c.name,
        image=c.image.tags[0] if c.image.tags else c.image.short_id,
        status=c.status,
        state=c.attrs.get("State", {}).get("Status", "unknown"),
        ports=ports_str,
        created=created,
    )


@router.get("", response_model=list[DockerContainerResponse])
async def list_containers(request: Request, all: bool = True) -> list[DockerContainerResponse]:
    """Daftar semua Docker container."""
    try:
        client = _get_docker_client()
        containers = client.containers.list(all=all)
        return [_format_container(c) for c in containers]
    except Exception as e:
        logger.error("Gagal list Docker containers.", error=str(e))
        return []


@router.post("/{container_id}/start", response_model=SuccessResponse)
async def start_container(container_id: str, request: Request) -> SuccessResponse:
    """Start Docker container."""
    try:
        client = _get_docker_client()
        c = client.containers.get(container_id)
        c.start()
        return SuccessResponse(message=f"Container '{c.name}' berhasil distart.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/stop", response_model=SuccessResponse)
async def stop_container(container_id: str, request: Request) -> SuccessResponse:
    """Stop Docker container."""
    try:
        client = _get_docker_client()
        c = client.containers.get(container_id)
        c.stop(timeout=10)
        return SuccessResponse(message=f"Container '{c.name}' berhasil distop.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/restart", response_model=SuccessResponse)
async def restart_container(container_id: str, request: Request) -> SuccessResponse:
    """Restart Docker container."""
    try:
        client = _get_docker_client()
        c = client.containers.get(container_id)
        c.restart(timeout=10)
        return SuccessResponse(message=f"Container '{c.name}' berhasil direstart.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{container_id}/logs")
async def get_logs(container_id: str, request: Request, tail: int = 100) -> dict:
    """Ambil log Docker container."""
    try:
        client = _get_docker_client()
        c = client.containers.get(container_id)
        logs = c.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        return {"logs": logs, "name": c.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
