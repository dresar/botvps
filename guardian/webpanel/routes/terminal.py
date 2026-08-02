"""Route /api/terminal — eksekusi shell command."""

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from guardian.webpanel.models import TerminalResponse

router = APIRouter(prefix="/api/terminal", tags=["terminal"])
logger = structlog.get_logger(__name__)


class RunCommandRequest(BaseModel):
    command: str
    user_id: int = 0


@router.post("/run", response_model=TerminalResponse)
async def run_command_endpoint(body: RunCommandRequest, request: Request) -> TerminalResponse:
    """Eksekusi perintah shell. User ID diambil dari auth middleware."""
    from guardian.core.engine import ApplicationContext
    ctx: ApplicationContext = request.app.state.guardian_ctx

    from guardian.plugins.terminal.service import TerminalService
    service = TerminalService(ctx)

    # Gunakan user_id dari header X-User-Id yang di-set oleh auth middleware
    user_id = getattr(request.state, "user_id", body.user_id) or 0

    result = await service.execute(user_id, body.command)

    return TerminalResponse(
        command=result.command,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        blocked=result.blocked,
        block_reason=result.block_reason,
        cwd=result.cwd,
    )


@router.get("/history")
async def get_history(request: Request, limit: int = 20) -> dict:
    """Riwayat perintah terminal untuk user ini."""
    from guardian.core.engine import ApplicationContext
    ctx: ApplicationContext = request.app.state.guardian_ctx

    from guardian.plugins.terminal.repository import TerminalRepository
    repo = TerminalRepository(ctx.database)

    user_id = getattr(request.state, "user_id", 0) or 0
    history = await repo.get_history(user_id, limit=limit)

    return {
        "history": [
            {
                "id": h.id,
                "command": h.command,
                "exit_code": h.exit_code,
                "executed_at": h.executed_at,
            }
            for h in history
        ]
    }
