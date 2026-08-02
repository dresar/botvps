"""FastAPI application untuk Web Panel — Telegram Mini App backend."""

import asyncio
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

import psutil
import structlog
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from guardian.webpanel.auth import extract_user_id
from guardian.webpanel.routes.ai import router as ai_router
from guardian.webpanel.routes.alerts import router as alerts_router
from guardian.webpanel.routes.docker import router as docker_router
from guardian.webpanel.routes.metrics import router as metrics_router
from guardian.webpanel.routes.services import router as services_router
from guardian.webpanel.routes.terminal import router as terminal_router

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def create_app(ctx: "ApplicationContext") -> FastAPI:
    """Buat FastAPI application dengan semua routes dan middleware.

    Args:
        ctx: ApplicationContext dari Guardian Engine.

    Returns:
        FastAPI application yang siap dijalankan.
    """
    app = FastAPI(
        title="Serverinka Guardian Web Panel",
        description="Telegram Mini App API untuk kontrol VPS",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
    )

    # Simpan ctx di app.state agar bisa diakses di routes
    app.state.guardian_ctx = ctx

    # CORS middleware
    cors_origins = ctx.settings.webpanel_cors_origins or "*"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cors_origins] if cors_origins != "*" else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------- Auth Middleware

    @app.middleware("http")
    async def telegram_auth_middleware(request: Request, call_next: object) -> object:
        """Verifikasi Telegram initData di setiap request API."""
        path = request.url.path

        # Lewati auth untuk static files dan health check
        if not path.startswith("/api/") or path == "/api/health":
            return await call_next(request)

        init_data = (
            request.headers.get("X-Telegram-Init-Data")
            or request.query_params.get("initData")
            or ""
        )

        # Di mode dev (no initData), izinkan dengan user_id=0
        user_id = 0
        if init_data:
            user_id = extract_user_id(init_data, ctx.settings.telegram_bot_token) or 0

            if user_id == 0:
                return JSONResponse(
                    {"error": "Unauthorized", "detail": "initData tidak valid atau kadaluarsa."},
                    status_code=401,
                )

            # Cek apakah user terdaftar sebagai admin
            try:
                admin_ids = ctx.settings.telegram_admin_user_ids
                if isinstance(admin_ids, list) and user_id not in admin_ids:
                    return JSONResponse(
                        {"error": "Forbidden", "detail": "Hanya admin yang boleh akses."},
                        status_code=403,
                    )
            except Exception:
                pass

        request.state.user_id = user_id
        return await call_next(request)

    # ---------------------------------------------------------------- Routers

    app.include_router(metrics_router)
    app.include_router(docker_router)
    app.include_router(services_router)
    app.include_router(terminal_router)
    app.include_router(alerts_router)
    app.include_router(ai_router)

    # ---------------------------------------------------------------- WebSocket

    @app.websocket("/ws/metrics")
    async def metrics_ws(websocket: WebSocket) -> None:
        """WebSocket endpoint untuk live metrics update setiap 3 detik."""
        await websocket.accept()
        logger.info("WebSocket client terhubung.", client=str(websocket.client))

        try:
            while True:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                load = psutil.getloadavg()
                boot = psutil.boot_time()

                payload = {
                    "ts": time.time(),
                    "cpu": cpu,
                    "ram": mem.percent,
                    "ram_used": mem.used,
                    "ram_total": mem.total,
                    "load1": load[0],
                    "load5": load[1],
                    "load15": load[2],
                    "uptime": int(time.time() - boot),
                }
                await websocket.send_text(json.dumps(payload))
                await asyncio.sleep(3)
        except WebSocketDisconnect:
            logger.info("WebSocket client terputus.")
        except Exception as e:
            logger.warning("WebSocket error.", error=str(e))

    # ---------------------------------------------------------------- Health

    @app.get("/api/health")
    async def health_check() -> dict:
        return {"status": "ok", "service": "Serverinka Guardian Web Panel"}

    # ---------------------------------------------------------------- Static files & SPA

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/", response_class=HTMLResponse)
        @app.get("/{path:path}", response_class=HTMLResponse)
        async def serve_spa(request: Request, path: str = "") -> FileResponse:
            """Serve Single Page Application."""
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return HTMLResponse("<h1>Panel tidak ditemukan</h1>", status_code=404)
    else:
        @app.get("/")
        async def no_static() -> dict:
            return {"message": "Static files belum tersedia."}

    return app
