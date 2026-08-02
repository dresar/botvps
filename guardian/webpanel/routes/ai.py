"""Route /api/ai — AI chat endpoint untuk Web Panel."""

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from guardian.webpanel.models import AIMessageResponse

router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = structlog.get_logger(__name__)


class AIChatRequest(BaseModel):
    message: str


@router.post("/chat", response_model=AIMessageResponse)
async def chat(body: AIChatRequest, request: Request) -> AIMessageResponse:
    """Kirim pesan ke AI Serverinka dari Web Panel."""
    from guardian.core.engine import ApplicationContext
    ctx: ApplicationContext = request.app.state.guardian_ctx

    user_id = getattr(request.state, "user_id", 0) or 0

    try:
        from guardian.plugins.ai_assistant.service import AIAssistantService
        service = AIAssistantService(ctx)
        response = await service.ask_ai(
            telegram_id=user_id,
            user_prompt=body.message,
        )
        # Strip HTML tags untuk response plain
        import re
        clean = re.sub(r"<[^>]+>", "", response)
        return AIMessageResponse(response=clean, provider=ctx.settings.ai_provider)
    except Exception as e:
        logger.error("AI chat error di web panel.", error=str(e))
        return AIMessageResponse(
            response=f"Maaf, terjadi error: {e}",
            provider="error",
        )
