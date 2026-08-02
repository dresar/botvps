"""Handlers untuk plugin user_manager."""

import structlog

from guardian.core.auth_service import ROLE_PERMISSIONS, VALID_ROLES
from guardian.core.bot_gateway import CommandContext
from guardian.core.exceptions import (
    InvalidRoleError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from guardian.utils.formatters import escape_html
from guardian.utils.validators import is_valid_role, is_valid_telegram_id

logger = structlog.get_logger(__name__)

ROLE_EMOJI = {
    "super_admin": "🔴",
    "admin": "🟠",
    "operator": "🟡",
    "viewer": "🟢",
}


class UserManagerHandlers:
    """Command handlers untuk user_manager plugin."""

    async def handle_list(self, ctx: CommandContext) -> None:
        """Tampilkan daftar semua pengguna terdaftar."""
        from guardian.plugins.user_manager.repository import UserRepository
        repo = UserRepository(ctx.app_ctx.database)
        users = await repo.find_all()

        if not users:
            await ctx.bot_gateway.send_message(ctx.chat_id, "ℹ️ Belum ada pengguna terdaftar.")
            return

        lines = ["👥 <b>Daftar Pengguna</b>\n"]
        for u in users:
            status = "✅" if u.is_active and not u.is_blocked else "❌"
            emoji = ROLE_EMOJI.get(u.role, "⚫")
            name = escape_html(u.full_name)
            username = f"@{u.username}" if u.username else "no username"
            lines.append(f"{status} {emoji} <b>{name}</b> ({username})\n   ID: <code>{u.telegram_id}</code> | Role: {u.role}")

        await ctx.bot_gateway.send_message(ctx.chat_id, "\n".join(lines))

    async def handle_add(self, ctx: CommandContext) -> None:
        """Tambah pengguna baru. Syntax: /user add [telegram_id] [role]"""
        if len(ctx.args) < 2:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/user add [telegram_id] [role]</code>\n\n"
                f"Role yang valid: {', '.join(sorted(VALID_ROLES))}",
            )
            return

        telegram_id_str, role = ctx.args[0], ctx.args[1].lower()

        if not is_valid_telegram_id(telegram_id_str):
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Telegram ID tidak valid. Harus berupa angka positif."
            )
            return

        if not is_valid_role(role):
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                f"❌ Role tidak valid. Pilihan: {', '.join(sorted(VALID_ROLES))}",
            )
            return

        if role == "super_admin" and ctx.user.role != "super_admin":
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "🚫 Hanya super_admin yang dapat menambah super_admin lain."
            )
            return

        telegram_id = int(telegram_id_str)

        try:
            new_user = await ctx.app_ctx.auth.add_user(
                telegram_id=telegram_id,
                username=None,
                full_name=f"User {telegram_id}",
                role=role,
                added_by=ctx.user.telegram_id,
            )
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                f"✅ <b>Pengguna Ditambahkan</b>\n\n"
                f"ID: <code>{new_user.telegram_id}</code>\n"
                f"Role: {new_user.role}",
            )
        except UserAlreadyExistsError:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ User dengan ID {telegram_id} sudah terdaftar."
            )
        except Exception as e:
            logger.exception("Gagal menambah user.", error=str(e))
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Gagal menambah pengguna.")

    async def handle_role(self, ctx: CommandContext) -> None:
        """Ubah role pengguna. Syntax: /user role [telegram_id] [new_role]"""
        if len(ctx.args) < 2:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/user role [telegram_id] [new_role]</code>",
            )
            return

        telegram_id_str, new_role = ctx.args[0], ctx.args[1].lower()

        if not is_valid_telegram_id(telegram_id_str):
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Telegram ID tidak valid.")
            return

        if not is_valid_role(new_role):
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"❌ Role tidak valid. Pilihan: {', '.join(sorted(VALID_ROLES))}"
            )
            return

        try:
            updated = await ctx.app_ctx.auth.update_user_role(
                telegram_id=int(telegram_id_str),
                new_role=new_role,
                updated_by=ctx.user.telegram_id,
            )
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                f"✅ Role user <code>{updated.telegram_id}</code> diubah menjadi <b>{new_role}</b>.",
            )
        except (UserNotFoundError, InvalidRoleError) as e:
            await ctx.bot_gateway.send_message(ctx.chat_id, f"❌ {e.message}")
        except Exception as e:
            logger.exception("Gagal mengubah role.", error=str(e))
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Gagal mengubah role.")

    async def handle_remove(self, ctx: CommandContext) -> None:
        """Nonaktifkan pengguna. Syntax: /user remove [telegram_id]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "ℹ️ <b>Penggunaan:</b> <code>/user remove [telegram_id]</code>",
            )
            return

        telegram_id_str = ctx.args[0]
        if not is_valid_telegram_id(telegram_id_str):
            await ctx.bot_gateway.send_message(ctx.chat_id, "❌ Telegram ID tidak valid.")
            return

        telegram_id = int(telegram_id_str)
        if telegram_id == ctx.user.telegram_id:
            await ctx.bot_gateway.send_message(
                ctx.chat_id, "❌ Anda tidak dapat menonaktifkan akun sendiri."
            )
            return

        try:
            await ctx.app_ctx.auth.deactivate_user(
                telegram_id=telegram_id,
                deactivated_by=ctx.user.telegram_id,
            )
            await ctx.bot_gateway.send_message(
                ctx.chat_id, f"✅ User <code>{telegram_id}</code> telah dinonaktifkan."
            )
        except (UserNotFoundError, Exception) as e:
            err_msg = e.message if hasattr(e, "message") else str(e)
            await ctx.bot_gateway.send_message(ctx.chat_id, f"❌ {err_msg}")
