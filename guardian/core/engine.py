"""Engine utama — ApplicationContext, startup, dan shutdown Serverinka Guardian."""

import asyncio
import signal
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog
from telegram import Bot
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.ext import CallbackQueryHandler

from guardian.core.auth_service import AuthService
from guardian.core.bot_gateway import BotGateway
from guardian.core.config import GuardianSettings
from guardian.core.database import DatabaseManager
from guardian.core.event_bus import EventBus
from guardian.core.plugin_manager import PluginManager
from guardian.core.scheduler import SchedulerEngine

logger = structlog.get_logger(__name__)


@dataclass
class ApplicationContext:
    """Container dependency injection untuk seluruh sistem.

    Semua komponen inti tersedia di sini dan diinjeksikan ke plugin.
    Plugin TIDAK boleh membuat instance komponen sendiri.
    """

    settings: GuardianSettings
    database: DatabaseManager
    event_bus: EventBus
    scheduler: SchedulerEngine
    auth: AuthService
    plugin_manager: PluginManager
    bot: BotGateway

    @property
    def db(self) -> DatabaseManager:
        """Alias untuk database."""
        return self.database


class GuardianEngine:
    """Engine utama Serverinka Guardian.

    Bertanggung jawab atas:
    - Inisialisasi seluruh komponen sistem.
    - Startup sequence yang terurut.
    - Graceful shutdown saat SIGTERM/SIGINT.

    Args:
        settings: Konfigurasi yang sudah divalidasi.
    """

    def __init__(self, settings: GuardianSettings) -> None:
        self._settings = settings
        self._app: Application | None = None
        self._ctx: ApplicationContext | None = None
        self._shutdown_event = asyncio.Event()

    async def run(self) -> None:
        """Mulai bot dan blokir hingga shutdown."""
        await self._startup()
        assert self._app is not None

        try:
            await self._app.start()
            await self._app.updater.start_polling(allowed_updates=["message", "callback_query"])
            logger.info("Bot aktif dan mendengarkan update...")

            await self._shutdown_event.wait()
        finally:
            await self._shutdown()

    async def _startup(self) -> None:
        """Urutan startup yang terstruktur."""
        logger.info("Memulai Serverinka Guardian...")

        db = DatabaseManager(self._settings.database_path)
        await db.initialize()

        event_bus = EventBus()

        auth = AuthService(
            db=db,
            event_bus=event_bus,
            settings=self._settings,
        )
        await auth.bootstrap_super_admins()

        scheduler = SchedulerEngine(db=db)

        plugin_manager = PluginManager(
            disabled_plugins=self._settings.disabled_plugins
        )

        telegram_app = (
            ApplicationBuilder()
            .token(self._settings.telegram_bot_token)
            .connect_timeout(self._settings.connect_timeout)
            .read_timeout(self._settings.read_timeout)
            .write_timeout(self._settings.write_timeout)
            .pool_timeout(self._settings.pool_timeout)
            .build()
        )

        bot_gateway = BotGateway(
            bot=telegram_app.bot,
            ctx=None,  # type: ignore[arg-type]
        )

        ctx = ApplicationContext(
            settings=self._settings,
            database=db,
            event_bus=event_bus,
            scheduler=scheduler,
            auth=auth,
            plugin_manager=plugin_manager,
            bot=bot_gateway,
        )

        bot_gateway._ctx = ctx

        self._ctx = ctx
        self._app = telegram_app

        async def message_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            from telegram import Update as TGUpdate
            if isinstance(update, TGUpdate):
                await bot_gateway.handle_update(update)

        async def callback_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            from telegram import Update as TGUpdate
            if isinstance(update, TGUpdate):
                await bot_gateway.handle_update(update)

        telegram_app.add_handler(
            MessageHandler(filters.ALL, message_handler)
        )
        telegram_app.add_handler(CallbackQueryHandler(callback_handler))

        await telegram_app.initialize()

        await plugin_manager.discover_and_load(ctx)
        scheduler.start()

        # Daftarkan perintah bot ke Telegram autocomplete menu (BotFather UI)
        await bot_gateway.register_botfather_commands()

        await event_bus.publish("system.startup_complete", {"version": "1.0.0"})

        # Kirim notifikasi bot aktif ke admin
        try:
            admin_ids = await auth.get_all_alert_recipient_ids()
            if admin_ids:
                import socket
                hostname = socket.gethostname()
                from guardian.utils.keyboard_builder import build_main_menu_keyboard
                msg = (
                    f"🚀 <b>Serverinka Guardian Berhasil Diaktifkan!</b>\n\n"
                    f"🖥️ Server: <code>{hostname}</code>\n"
                    f"⚙️ Status: Online & Siap Digunakan!\n"
                    f"🔌 Plugin: {len(plugin_manager.loaded_plugins)} plugin dimuat."
                )
                await bot_gateway.broadcast(admin_ids, msg, keyboard=build_main_menu_keyboard())
        except Exception:
            logger.warning("Gagal mengirim notifikasi startup ke admin.")

        self._register_signal_handlers()

        logger.info(
            "Startup selesai.",
            plugins_loaded=len(plugin_manager.loaded_plugins),
        )

    async def _shutdown(self) -> None:
        """Urutan shutdown yang graceful."""
        logger.info("Mematikan Serverinka Guardian...")

        if self._ctx:
            await self._ctx.event_bus.publish("system.shutdown_requested", {})
            await self._ctx.plugin_manager.teardown_all()
            self._ctx.scheduler.stop()
            await self._ctx.database.close()

        if self._app:
            try:
                await self._app.updater.stop()
                await self._app.stop()
                await self._app.shutdown()
            except Exception:
                logger.exception("Error saat shutdown Telegram Application.")

        logger.info("Serverinka Guardian berhasil dihentikan.")

    def _register_signal_handlers(self) -> None:
        """Daftarkan handler untuk sinyal OS (SIGTERM, SIGINT)."""
        loop = asyncio.get_event_loop()

        def _request_shutdown(sig_name: str) -> None:
            logger.info("Sinyal diterima, memulai shutdown...", signal=sig_name)
            self._shutdown_event.set()

        try:
            loop.add_signal_handler(signal.SIGTERM, lambda: _request_shutdown("SIGTERM"))
            loop.add_signal_handler(signal.SIGINT, lambda: _request_shutdown("SIGINT"))
        except NotImplementedError:
            logger.warning("Signal handler tidak didukung di platform ini (Windows).")
