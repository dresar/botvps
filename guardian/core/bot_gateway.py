"""BotGateway — wrapper Telegram API untuk Serverinka Guardian."""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog
from telegram import (
    Bot,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

from guardian.core.auth_service import AuthResult, UserDTO
from guardian.core.exceptions import RateLimitError
from guardian.utils.message_builder import build_denied_message, split_long_message

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)

MAX_MESSAGE_LENGTH = 4096


@dataclass
class CommandContext:
    """Context yang diteruskan ke setiap command handler."""

    user: UserDTO
    chat_id: int
    message_id: int
    command: str
    args: list[str]
    raw_text: str
    update: Update
    bot_gateway: "BotGateway"
    app_ctx: "ApplicationContext"

    async def respond(
        self,
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
        parse_mode: str = ParseMode.HTML,
    ) -> Message | None:
        """Kirim pesan baru jika diketik manual, atau EDIT pesan yang ada jika ditekan via tombol inline."""
        if self.update and self.update.callback_query and self.message_id:
            return await self.bot_gateway.edit_message(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=text,
                keyboard=keyboard,
                parse_mode=parse_mode,
            )
        return await self.bot_gateway.send_message(
            chat_id=self.chat_id,
            text=text,
            keyboard=keyboard,
            parse_mode=parse_mode,
        )


@dataclass
class CallbackContext:
    """Context yang diteruskan ke setiap callback query handler."""

    user: UserDTO
    chat_id: int
    message_id: int
    callback_query_id: str
    data: str
    update: Update
    bot_gateway: "BotGateway"
    app_ctx: "ApplicationContext"


@dataclass
class BroadcastResult:
    """Hasil broadcast pesan ke banyak user."""

    sent_count: int
    failed_count: int
    failed_user_ids: list[int]


class BotGateway:
    """Wrapper di atas Telegram Bot API.

    Menangani:
    - Middleware chain (auth, rate limit, audit).
    - Routing command ke plugin handler.
    - Pengiriman pesan dan dokumen.
    - Broadcast ke banyak user.

    Args:
        bot: Telegram Bot instance.
        ctx: ApplicationContext.
    """

    def __init__(self, bot: Bot, ctx: "ApplicationContext") -> None:
        self._bot = bot
        self._ctx = ctx
        self._rate_limit_cache: dict[int, list[float]] = {}

    async def send_message(
        self,
        chat_id: int,
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
        parse_mode: str = ParseMode.HTML,
    ) -> Message | None:
        """Kirim pesan ke chat.

        Args:
            chat_id: ID chat tujuan.
            text: Teks pesan (HTML atau plain).
            keyboard: Inline keyboard opsional.
            parse_mode: Mode parsing teks.

        Returns:
            Message object atau None jika gagal.
        """
        try:
            return await self._bot.send_message(
                chat_id=chat_id,
                text=text[:MAX_MESSAGE_LENGTH],
                reply_markup=keyboard,
                parse_mode=parse_mode,
            )
        except Exception as e:
            logger.error("Gagal mengirim pesan.", chat_id=chat_id, error=str(e))
            return None

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> bool:
        """Kirim indikator status aktivitas Telegram (misal: typing / mengetik)."""
        try:
            await self._bot.send_chat_action(chat_id=chat_id, action=action)
            return True
        except Exception as e:
            logger.debug("Gagal mengirim chat action.", chat_id=chat_id, error=str(e))
            return False

    async def send_long_message(
        self,
        chat_id: int,
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
    ) -> list[Message]:
        """Kirim pesan panjang yang dipecah otomatis.

        Args:
            chat_id: ID chat tujuan.
            text: Teks pesan (bisa lebih dari 4096 karakter).
            keyboard: Keyboard hanya pada pesan terakhir.

        Returns:
            List Message yang terkirim.
        """
        parts = split_long_message(text)
        messages = []

        for i, part in enumerate(parts):
            kb = keyboard if i == len(parts) - 1 else None
            msg = await self.send_message(chat_id, part, keyboard=kb)
            if msg:
                messages.append(msg)

        return messages

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
        parse_mode: str = ParseMode.HTML,
    ) -> Message | None:
        """Edit pesan yang sudah ada.

        Args:
            chat_id: ID chat.
            message_id: ID pesan yang akan diedit.
            text: Teks baru.
            keyboard: Keyboard baru.
            parse_mode: Mode parsing.

        Returns:
            Message object atau None jika gagal.
        """
        try:
            result = await self._bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text[:MAX_MESSAGE_LENGTH],
                reply_markup=keyboard,
                parse_mode=parse_mode,
            )
            if isinstance(result, Message):
                return result
            return None
        except TelegramError as e:
            if "message is not modified" not in str(e).lower():
                logger.warning("Gagal mengedit pesan.", error=str(e))
            return None

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = "",
        show_alert: bool = False,
    ) -> None:
        """Jawab callback query (menghentikan loading indicator).

        Args:
            callback_query_id: ID callback query.
            text: Teks notifikasi singkat (opsional).
            show_alert: Tampilkan sebagai alert dialog.
        """
        try:
            await self._bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text[:200] if text else "",
                show_alert=show_alert,
            )
        except TelegramError as e:
            logger.debug("Gagal answer callback query.", error=str(e))

    async def send_document(
        self,
        chat_id: int,
        document: bytes,
        filename: str,
        caption: str = "",
    ) -> Message | None:
        """Kirim file dokumen ke chat.

        Args:
            chat_id: ID chat.
            document: Konten file dalam bytes.
            filename: Nama file.
            caption: Caption opsional.

        Returns:
            Message object atau None jika gagal.
        """
        import io
        try:
            return await self._bot.send_document(
                chat_id=chat_id,
                document=io.BytesIO(document),
                filename=filename,
                caption=caption[:1024] if caption else "",
            )
        except TelegramError as e:
            logger.error("Gagal mengirim dokumen.", chat_id=chat_id, error=str(e))
            return None

    async def broadcast(
        self,
        user_ids: list[int],
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
    ) -> BroadcastResult:
        """Kirim pesan ke banyak user.

        Args:
            user_ids: List Telegram user ID tujuan.
            text: Teks pesan.
            keyboard: Keyboard opsional.

        Returns:
            BroadcastResult dengan statistik pengiriman.
        """
        sent = 0
        failed = 0
        failed_ids = []

        for user_id in user_ids:
            msg = await self.send_message(user_id, text, keyboard=keyboard)
            if msg:
                sent += 1
            else:
                failed += 1
                failed_ids.append(user_id)

        return BroadcastResult(
            sent_count=sent,
            failed_count=failed,
            failed_user_ids=failed_ids,
        )

    async def register_botfather_commands(self) -> None:
        """Daftarkan seluruh perintah bot ke Telegram BotFather autocomplete menu."""
        from telegram import BotCommand

        commands = [
            BotCommand("start", "🏠 Dashboard Menu Utama"),
            BotCommand("status", "📊 Cek resource VPS (CPU, RAM, Disk)"),
            BotCommand("ask", "🧠 AI Assistant Gemini (Konteks VPS & Memory)"),
            BotCommand("cpu_guard", "🛡️ Dashboard & Kontrol Auto Process CPU Guardian"),
            BotCommand("package_guard", "📦 Dashboard & Kontrol Package Protection"),
            BotCommand("service", "⚙️ Manajemen Layanan Systemd VPS"),
            BotCommand("docker", "🐳 Manajemen Kontainer Docker"),
            BotCommand("alert", "🔔 Pengaturan Notifikasi Alert"),
            BotCommand("schedule", "📅 Pengaturan Jadwal Task Otomatis"),
            BotCommand("user", "👥 Manajemen Pengguna & Hak Akses"),
            BotCommand("audit", "📋 Lihat Log Audit Aktivitas"),
        ]
        try:
            await self._bot.set_my_commands(commands)
            logger.info("Perintah bot berhasil didaftarkan ke Telegram autocomplete menu.")
        except Exception as e:
            logger.warning("Gagal menyinkronkan set_my_commands ke Telegram API.", error=str(e))

    async def handle_update(self, update: Update) -> None:
        """Proses update dari Telegram melalui middleware chain.

        Args:
            update: Telegram Update object.
        """
        if update.message and update.message.text:
            await self._handle_message(update)
        elif update.callback_query:
            await self._handle_callback(update)

    async def _handle_message(self, update: Update) -> None:
        """Handle pesan masuk dari user."""
        message = update.message
        if not message or not message.from_user:
            return

        telegram_user = message.from_user
        chat_id = message.chat_id
        text = message.text or ""

        auth_result = await self._ctx.auth.authenticate(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            full_name=telegram_user.full_name,
        )

        if not auth_result.is_authorized:
            await self.send_message(
                chat_id,
                build_denied_message(auth_result.denial_reason or ""),
            )
            return

        user = auth_result.user
        assert user is not None

        if not self._check_rate_limit(user.telegram_id):
            window = self._ctx.settings.rate_limit_window_seconds
            await self.send_message(
                chat_id,
                f"⏳ <b>Terlalu Banyak Perintah</b>\n\nCoba lagi dalam {window} detik.",
            )
            return

        await self._route_command(update, user, chat_id, text)

    async def _handle_callback(self, update: Update) -> None:
        """Handle callback query dari inline keyboard."""
        query = update.callback_query
        if not query or not query.from_user:
            return

        telegram_user = query.from_user
        data = query.data or ""

        if data in ("nav:noop",):
            await self.answer_callback_query(query.id)
            return

        auth_result = await self._ctx.auth.authenticate(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            full_name=telegram_user.full_name,
        )

        if not auth_result.is_authorized:
            await self.answer_callback_query(
                query.id,
                text="Akses ditolak.",
                show_alert=True,
            )
            return

        user = auth_result.user
        assert user is not None

        handler = self._ctx.plugin_manager.get_callback_handler(data)

        if data == "nav:main_menu":
            from guardian.utils.keyboard_builder import build_main_menu_keyboard
            from guardian.utils.message_builder import build_header
            await self.answer_callback_query(query.id)
            if query.message:
                await self.edit_message(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=build_header("🤖 Serverinka Guardian", "Pilih menu:"),
                    keyboard=build_main_menu_keyboard(),
                )
            return

        NAV_COMMAND_MAP = {
            "nav:system_status": ("system", "status"),
            "nav:service_list": ("service", "list"),
            "nav:docker_list": ("docker", "list"),
            "nav:cpu_guard_status": ("cpu_guard", "menu"),
            "nav:package_guard_status": ("package_guard", "menu"),
            "nav:alert_list": ("alert", "list"),
            "nav:schedule_list": ("schedule", "list"),
            "nav:user_list": ("user", "list"),
            "nav:ai_help": ("ask", "menu"),
            "nav:audit_list": ("audit", "list"),
            "nav:settings": ("system", "status"),
        }

        if data in NAV_COMMAND_MAP:
            namespace, command = NAV_COMMAND_MAP[data]
            registered = self._ctx.plugin_manager.get_command(namespace, command)
            if registered:
                cmd_ctx = CommandContext(
                    user=user,
                    chat_id=query.message.chat_id if query.message else telegram_user.id,
                    message_id=query.message.message_id if query.message else 0,
                    command=command,
                    args=[],
                    raw_text=f"/{namespace} {command}",
                    update=update,
                    bot_gateway=self,
                    app_ctx=self._ctx,
                )
                await self.answer_callback_query(query.id)
                await registered.handler(cmd_ctx)
                return

        if handler:
            callback_ctx = CallbackContext(
                user=user,
                chat_id=query.message.chat_id if query.message else telegram_user.id,
                message_id=query.message.message_id if query.message else 0,
                callback_query_id=query.id,
                data=data,
                update=update,
                bot_gateway=self,
                app_ctx=self._ctx,
            )
            try:
                await self.answer_callback_query(query.id)
                await handler(callback_ctx)
            except Exception:
                logger.exception("Error pada callback handler.", data=data)
                await self.answer_callback_query(query.id, text="Terjadi kesalahan.", show_alert=True)
        else:
            # Fallback: jika format data adalah namespace:command
            if ":" in data:
                parts = data.split(":", 1)
                registered = self._ctx.plugin_manager.get_command(parts[0], parts[1])
                if registered:
                    cmd_ctx = CommandContext(
                        user=user,
                        chat_id=query.message.chat_id if query.message else telegram_user.id,
                        message_id=query.message.message_id if query.message else 0,
                        command=parts[1],
                        args=[],
                        raw_text=f"/{parts[0]} {parts[1]}",
                        update=update,
                        bot_gateway=self,
                        app_ctx=self._ctx,
                    )
                    await self.answer_callback_query(query.id)
                    await registered.handler(cmd_ctx)
                    return

            await self.answer_callback_query(query.id, text="Perintah tidak dikenali.")

    async def _route_command(
        self,
        update: Update,
        user: UserDTO,
        chat_id: int,
        text: str,
    ) -> None:
        """Route command ke plugin handler yang sesuai."""
        if not text.startswith("/"):
            # Jika pesan berupa teks biasa tanpa /, teruskan langsung ke AI Assistant
            ai_cmd = self._ctx.plugin_manager.get_command("ask", "menu")
            if ai_cmd:
                cmd_ctx = CommandContext(
                    user=user,
                    chat_id=chat_id,
                    message_id=update.message.message_id if update.message else 0,
                    command="menu",
                    args=text.split(),
                    raw_text=text,
                    update=update,
                    bot_gateway=self,
                    app_ctx=self._ctx,
                )
                await ai_cmd.handler(cmd_ctx)
            return

        parts = text.split()
        raw_command = parts[0].lstrip("/").lower().split("@")[0]
        args = parts[1:] if len(parts) > 1 else []

        SHORTCUTS = {
            "start": ("nav", "start"),
            "menu": ("nav", "menu"),
            "help": ("nav", "help"),
            "status": ("system", "status"),
            "cancel": ("nav", "cancel"),
            "ask": ("ask", "menu"),
            "ai": ("ai", "ask"),
        }

        if raw_command in SHORTCUTS:
            namespace, command = SHORTCUTS[raw_command]
        elif ":" in raw_command:
            namespace, command = raw_command.split(":", 1)
        else:
            namespace = raw_command
            if args and self._ctx.plugin_manager.get_command(namespace, args[0].lower()):
                command = args[0].lower()
                args = args[1:]
            else:
                if self._ctx.plugin_manager.get_command(namespace, "menu"):
                    command = "menu"
                elif self._ctx.plugin_manager.get_command(namespace, "list"):
                    command = "list"
                else:
                    command = "status"

        registered = self._ctx.plugin_manager.get_command(namespace, command)

        if registered is None:
            if raw_command in ("start", "menu") or namespace in ("start", "menu"):
                from guardian.utils.keyboard_builder import build_main_menu_keyboard
                from guardian.utils.message_builder import build_header
                await self.send_message(
                    chat_id,
                    build_header("🤖 Serverinka Guardian", "Pilih menu:"),
                    keyboard=build_main_menu_keyboard(),
                )
            elif raw_command == "help" or namespace == "help":
                await self._send_help(chat_id, user)
            else:
                await self.send_message(
                    chat_id,
                    f"❌ <b>Perintah Tidak Dikenali</b>\n\nPerintah <code>/{escape_html(raw_command)}</code> tidak ditemukan. Gunakan menu <code>/start</code> atau <code>/help</code>.",
                )
            return

        for perm in registered.permissions:
            if not await self._ctx.auth.has_permission(user.telegram_id, perm):
                await self.send_message(chat_id, build_denied_message())
                return

        cmd_ctx = CommandContext(
            user=user,
            chat_id=chat_id,
            message_id=update.message.message_id if update.message else 0,
            command=command,
            args=args,
            raw_text=text,
            update=update,
            bot_gateway=self,
            app_ctx=self._ctx,
        )

        try:
            await registered.handler(cmd_ctx)
        except Exception:
            logger.exception("Error pada command handler.", command=f"{namespace}:{command}")
            await self.send_message(
                chat_id,
                "❌ <b>Terjadi Kesalahan</b>\n\nError dicatat. Hubungi administrator jika berlanjut.",
            )

    async def _send_help(self, chat_id: int, user: UserDTO) -> None:
        """Kirim pesan bantuan berisi daftar command."""
        commands = self._ctx.plugin_manager.get_all_commands()

        lines = ["📖 <b>Daftar Perintah</b>\n"]
        for cmd in commands:
            if not cmd.permissions:
                has_access = True
            else:
                has_access = all(
                    await self._ctx.auth.has_permission(user.telegram_id, p)
                    for p in cmd.permissions
                )
            if has_access and cmd.description:
                lines.append(f"/{cmd.namespace} {cmd.command} — {cmd.description}")

        if len(lines) == 1:
            lines.append("Tidak ada perintah yang tersedia.")

        await self.send_message(chat_id, "\n".join(lines))

    def _check_rate_limit(self, telegram_id: int) -> bool:
        """Cek apakah user masih dalam batas rate limit.

        Args:
            telegram_id: Telegram User ID.

        Returns:
            True jika masih diizinkan, False jika rate limit terlampaui.
        """
        now = time.monotonic()
        window = self._ctx.settings.rate_limit_window_seconds
        max_commands = self._ctx.settings.rate_limit_commands_per_window

        if telegram_id not in self._rate_limit_cache:
            self._rate_limit_cache[telegram_id] = []

        timestamps = [t for t in self._rate_limit_cache[telegram_id] if now - t < window]
        timestamps.append(now)
        self._rate_limit_cache[telegram_id] = timestamps

        return len(timestamps) <= max_commands
