"""Route /api/services — manajemen Systemd service."""

import asyncio

import structlog
from fastapi import APIRouter, HTTPException, Request

from guardian.utils.sandbox import run_command
from guardian.webpanel.models import ServiceResponse, SuccessResponse

router = APIRouter(prefix="/api/services", tags=["services"])
logger = structlog.get_logger(__name__)


async def _get_service_info(name: str) -> ServiceResponse:
    result = await run_command(
        ["systemctl", "show", name, "--no-pager",
         "--property=Description,ActiveState,SubState,UnitFileState"],
        timeout=10.0,
    )
    props: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            props[k.strip()] = v.strip()

    active = props.get("ActiveState", "unknown")
    sub = props.get("SubState", "unknown")
    enabled = props.get("UnitFileState", "disabled") in ("enabled", "enabled-runtime")

    status_map = {
        "active": "running",
        "inactive": "stopped",
        "failed": "failed",
        "activating": "starting",
        "deactivating": "stopping",
    }
    return ServiceResponse(
        name=name,
        description=props.get("Description", name),
        status=status_map.get(active, active),
        active_state=active,
        sub_state=sub,
        enabled=enabled,
    )


@router.get("", response_model=list[ServiceResponse])
async def list_services(request: Request) -> list[ServiceResponse]:
    """Daftar service systemd yang aktif/penting."""
    result = await run_command(
        ["systemctl", "list-units", "--type=service", "--no-pager", "--no-legend",
         "--state=loaded", "--plain"],
        timeout=15.0,
    )
    services = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        name = parts[0].replace(".service", "")
        if name in seen or name.startswith("@"):
            continue
        seen.add(name)
        try:
            svc = await _get_service_info(name + ".service")
            services.append(svc)
        except Exception:
            continue
    return services[:50]


@router.get("/{service_name}", response_model=ServiceResponse)
async def get_service(service_name: str, request: Request) -> ServiceResponse:
    """Detail satu service systemd."""
    return await _get_service_info(service_name + ".service")


@router.post("/{service_name}/start", response_model=SuccessResponse)
async def start_service(service_name: str, request: Request) -> SuccessResponse:
    result = await run_command(["systemctl", "start", service_name + ".service"], timeout=20.0)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.stderr or "Gagal start service.")
    return SuccessResponse(message=f"Service '{service_name}' berhasil distart.")


@router.post("/{service_name}/stop", response_model=SuccessResponse)
async def stop_service(service_name: str, request: Request) -> SuccessResponse:
    result = await run_command(["systemctl", "stop", service_name + ".service"], timeout=20.0)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.stderr or "Gagal stop service.")
    return SuccessResponse(message=f"Service '{service_name}' berhasil distop.")


@router.post("/{service_name}/restart", response_model=SuccessResponse)
async def restart_service(service_name: str, request: Request) -> SuccessResponse:
    result = await run_command(["systemctl", "restart", service_name + ".service"], timeout=20.0)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.stderr or "Gagal restart service.")
    return SuccessResponse(message=f"Service '{service_name}' berhasil direstart.")


@router.get("/{service_name}/logs")
async def get_service_logs(service_name: str, request: Request, lines: int = 100) -> dict:
    result = await run_command(
        ["journalctl", "-u", service_name + ".service", f"-n{lines}", "--no-pager"],
        timeout=15.0,
    )
    return {"logs": result.stdout, "service": service_name}
