"""Keyboard builder khusus untuk Terminal Plugin."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from guardian.utils.keyboard_builder import nav_row


def build_terminal_keyboard() -> InlineKeyboardMarkup:
    """Buat keyboard navigasi untuk halaman output terminal."""
    keyboard = [
        [
            InlineKeyboardButton("📋 Riwayat", callback_data="terminal:history"),
            InlineKeyboardButton("🔄 Reset Session", callback_data="terminal:reset"),
            InlineKeyboardButton("🗑️ Hapus History", callback_data="terminal:clear_history"),
        ],
        [
            InlineKeyboardButton("🖥️ Info Terminal", callback_data="terminal:menu"),
        ],
        nav_row(main_menu=True),
    ]
    return InlineKeyboardMarkup(keyboard)
