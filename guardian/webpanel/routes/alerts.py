"""Route /api/alerts — manajemen alert & notifikasi."""

import structlog
from fastapi import APIRouter, Request

from guardian.webpanel.models import AlertResponse, SuccessResponse

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = structlog.get_logger(__name__)


@router.get("", response_model=list[AlertResponse])
async def list_alerts(request: Request) -> list[AlertResponse]:
    """Daftar semua alert yang terdaftar."""
    from guardian.core.engine import ApplicationContext
    ctx: ApplicationContext = request.app.state.guardian_ctx

    try:
        from guardian.plugins.notification.repository import AlertRepository
        repo = AlertRepository(ctx.database)
        alerts = await repo.get_all_alerts()
        return [
            AlertResponse(
                id=a.id,
                name=a.name,
                metric=a.metric_type,
                threshold=a.threshold,
                current_value=None,
                is_enabled=a.is_enabled,
                last_triggered=a.last_triggered_at,
            )
            for a in alerts
        ]
    except Exception as e:
        logger.error("Gagal ambil alerts.", error=str(e))
        return []


@router.post("/{alert_id}/toggle", response_model=SuccessResponse)
async def toggle_alert(alert_id: int, request: Request) -> SuccessResponse:
    """Aktifkan/nonaktifkan alert."""
    from guardian.core.engine import ApplicationContext
    ctx: ApplicationContext = request.app.state.guardian_ctx

    try:
        from guardian.plugins.notification.repository import AlertRepository
        repo = AlertRepository(ctx.database)
        alert = await repo.get_alert_by_id(alert_id)
        if not alert:
            return SuccessResponse(message="Alert tidak ditemukan.")
        new_state = not alert.is_enabled
        await repo.set_alert_enabled(alert_id, new_state)
        state_str = "diaktifkan" if new_state else "dinonaktifkan"
        return SuccessResponse(message=f"Alert '{alert.name}' berhasil {state_str}.")
    except Exception as e:
        return SuccessResponse(message=f"Error: {e}")
