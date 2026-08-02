"""Handlers untuk WebPanel Plugin — command /panel."""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from guardian.core.bot_gateway import CommandContext
from guardian.utils.keyboard_builder import nav_row

logger = structlog.get_logger(__name__)


class WebPanelHandlers:
    """Handler command /panel."""

    async def handle_open_panel(self, ctx: CommandContext) -> None:
        """Tampilkan pesan dengan tombol yang membuka Telegram Mini App."""
        settings = ctx.app_ctx.settings
        webpanel_url = getattr(settings, "webpanel_url", "")
        port = getattr(settings, "webpanel_port", 8080)

        if not webpanel_url:
            # Fallback: tampilkan instruksi konfigurasi
            text = (
                "🌐 <b>Serverinka Web Panel</b>\n\n"
                "⚠️ <b>URL Web Panel belum dikonfigurasi.</b>\n\n"
                "Tambahkan di file <code>.env</code>:\n"
                f"<code>WEBPANEL_URL=https://namadomain.com:{port}</code>\n\n"
                f"🔧 Web Panel API berjalan di port <code>{port}</code>.\n"
                "Pastikan port sudah dibuka di firewall:\n"
                f"<code>ufw allow {port}/tcp</code>"
            )
            keyboard = InlineKeyboardMarkup([nav_row(main_menu=True)])
            await ctx.respond(text, keyboard=keyboard)
            return

        # Pastikan URL tidak ada trailing slash
        url = webpanel_url.rstrip("/")

        text = (
            "🌐 <b>Serverinka Web Panel</b>\n\n"
            "Panel kontrol VPS lengkap — dashboard real-time, "
            "Docker, Services, Terminal, AI Chat, dan banyak lagi!\n\n"
            "✅ Klik tombol di bawah untuk membuka panel:"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🌐 Buka Web Panel VPS",
                web_app=WebAppInfo(url=url),
            )],
            nav_row(main_menu=True),
        ])

        await ctx.respond(text, keyboard=keyboard)
