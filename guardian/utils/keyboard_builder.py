"""Builder untuk InlineKeyboard Telegram."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def nav_row(back_data: str | None = None, main_menu: bool = True) -> list[InlineKeyboardButton]:
    """Buat baris navigasi standar (Kembali + Menu Utama).

    Args:
        back_data: Callback data untuk tombol Kembali (None = tidak tampilkan).
        main_menu: Tampilkan tombol Menu Utama.

    Returns:
        List InlineKeyboardButton untuk baris navigasi.
    """
    row = []
    if back_data:
        row.append(InlineKeyboardButton("⬅️ Kembali", callback_data=back_data))
    if main_menu:
        row.append(InlineKeyboardButton("🏠 Menu Utama", callback_data="nav:main_menu"))
    return row


def refresh_row(refresh_data: str) -> list[InlineKeyboardButton]:
    """Buat baris dengan tombol refresh.

    Args:
        refresh_data: Callback data untuk refresh.

    Returns:
        List InlineKeyboardButton.
    """
    return [InlineKeyboardButton("🔄 Refresh", callback_data=refresh_data)]


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Buat keyboard untuk menu utama yang lengkap.

    Returns:
        InlineKeyboardMarkup menu utama.
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Status System", callback_data="nav:system_status"),
            InlineKeyboardButton("⚙️ Layanan Systemd", callback_data="nav:service_list"),
        ],
        [
            InlineKeyboardButton("🐳 Docker Containers", callback_data="nav:docker_list"),
            InlineKeyboardButton("🛡️ CPU Guard", callback_data="nav:cpu_guard_status"),
        ],
        [
            InlineKeyboardButton("📦 Package Protection", callback_data="nav:package_guard_status"),
            InlineKeyboardButton("🔔 Alert Notifikasi", callback_data="nav:alert_list"),
        ],
        [
            InlineKeyboardButton("📅 Jadwal Task", callback_data="nav:schedule_list"),
            InlineKeyboardButton("👥 Pengguna & Akses", callback_data="nav:user_list"),
        ],
        [
            InlineKeyboardButton("🧠 AI Assistant", callback_data="nav:ai_help"),
            InlineKeyboardButton("📋 Audit Log", callback_data="nav:audit_list"),
        ],
        [
            InlineKeyboardButton("🖥️ Terminal Shell", callback_data="terminal:menu"),
            InlineKeyboardButton("📋 Riwayat Terminal", callback_data="terminal:history"),
        ],
        [
            InlineKeyboardButton("🌐 Web Panel (Mini App)", callback_data="webpanel:open"),
        ],
        [
            InlineKeyboardButton("⚙️ Pengaturan System", callback_data="nav:settings"),
            InlineKeyboardButton("🔄 Refresh Menu", callback_data="nav:main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_confirmation_keyboard(yes_data: str, no_data: str = "confirm:no") -> InlineKeyboardMarkup:
    """Buat keyboard konfirmasi Ya/Tidak.

    Args:
        yes_data: Callback data untuk tombol Ya.
        no_data: Callback data untuk tombol Tidak.

    Returns:
        InlineKeyboardMarkup konfirmasi.
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Ya, Lanjut", callback_data=yes_data),
            InlineKeyboardButton("❌ Tidak, Batal", callback_data=no_data),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_service_action_keyboard(
    service_name: str, back_data: str = "nav:service_list"
) -> InlineKeyboardMarkup:
    """Buat keyboard aksi untuk layanan systemd.

    Args:
        service_name: Nama layanan.
        back_data: Callback data untuk Kembali.

    Returns:
        InlineKeyboardMarkup aksi layanan.
    """
    sn = service_name
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start", callback_data=f"service:start:{sn}"),
            InlineKeyboardButton("⏹️ Stop", callback_data=f"service:stop:{sn}"),
            InlineKeyboardButton("🔄 Restart", callback_data=f"service:restart:{sn}"),
        ],
        [
            InlineKeyboardButton("📋 Log", callback_data=f"service:log:{sn}"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"service:detail:{sn}"),
        ],
        nav_row(back_data=back_data),
    ]
    return InlineKeyboardMarkup(keyboard)


def build_container_action_keyboard(
    container_name: str, back_data: str = "nav:docker_list"
) -> InlineKeyboardMarkup:
    """Buat keyboard aksi untuk kontainer Docker.

    Args:
        container_name: Nama kontainer.
        back_data: Callback data untuk Kembali.

    Returns:
        InlineKeyboardMarkup aksi kontainer.
    """
    cn = container_name
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start", callback_data=f"docker:start:{cn}"),
            InlineKeyboardButton("⏹️ Stop", callback_data=f"docker:stop:{cn}"),
            InlineKeyboardButton("🔄 Restart", callback_data=f"docker:restart:{cn}"),
        ],
        [
            InlineKeyboardButton("📋 Log", callback_data=f"docker:log:{cn}"),
            InlineKeyboardButton("📊 Stats", callback_data=f"docker:stats:{cn}"),
        ],
        nav_row(back_data=back_data),
    ]
    return InlineKeyboardMarkup(keyboard)


def build_pagination_keyboard(
    context: str,
    current_page: int,
    total_pages: int,
    back_data: str | None = None,
) -> InlineKeyboardMarkup:
    """Buat keyboard navigasi pagination.

    Args:
        context: Konteks pagination, misal "docker_list".
        current_page: Halaman saat ini (1-indexed).
        total_pages: Total halaman.
        back_data: Callback data untuk Kembali.

    Returns:
        InlineKeyboardMarkup dengan tombol pagination.
    """
    rows: list[list[InlineKeyboardButton]] = []
    nav_buttons = []

    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Prev", callback_data=f"nav:page:{context}:{current_page - 1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(
            f"Hal {current_page}/{total_pages}", callback_data="nav:noop"
        )
    )

    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"nav:page:{context}:{current_page + 1}")
        )

    rows.append(nav_buttons)
    rows.append(nav_row(back_data=back_data))

    return InlineKeyboardMarkup(rows)


def build_sub_dashboard_keyboard(
    extra_buttons: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    """Buat keyboard navigasi seragam untuk seluruh sub-dashboard.

    Menampilkan tombol aksi internal sub-dashboard + tombol pintas navigasi langsung ke dashboard lain.
    """
    rows: list[list[InlineKeyboardButton]] = []
    if extra_buttons:
        rows.extend(extra_buttons)

    quick_nav = [
        [
            InlineKeyboardButton("📊 Status", callback_data="nav:system_status"),
            InlineKeyboardButton("🛡️ CPU Guard", callback_data="nav:cpu_guard_status"),
            InlineKeyboardButton("📦 Package", callback_data="nav:package_guard_status"),
        ],
        [
            InlineKeyboardButton("⚙️ Layanan", callback_data="nav:service_list"),
            InlineKeyboardButton("🐳 Docker", callback_data="nav:docker_list"),
            InlineKeyboardButton("🧠 AI Chat", callback_data="nav:ai_help"),
        ],
        [
            InlineKeyboardButton("🖥️ Terminal", callback_data="terminal:menu"),
            InlineKeyboardButton("⚙️ Pengaturan", callback_data="nav:settings"),
            InlineKeyboardButton("🏠 Menu Utama", callback_data="nav:main_menu"),
        ],
    ]

    rows.extend(quick_nav)
    return InlineKeyboardMarkup(rows)


def build_system_status_keyboard() -> InlineKeyboardMarkup:
    """Buat keyboard untuk halaman status sistem."""
    extra = [
        [
            InlineKeyboardButton("🔄 Refresh Status", callback_data="system:status"),
            InlineKeyboardButton("⚡ Top Proses", callback_data="system:proc"),
            InlineKeyboardButton("🌐 Jaringan", callback_data="system:net"),
        ],
        [
            InlineKeyboardButton("🔁 Reboot Server", callback_data="system:confirm_reboot"),
        ],
    ]
    return build_sub_dashboard_keyboard(extra)
