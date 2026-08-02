"""Builder untuk pesan Telegram dalam format HTML."""

from guardian.utils.formatters import (
    escape_html,
    format_bytes,
    format_load_average,
    format_uptime,
    make_progress_bar,
)


def build_header(title: str, subtitle: str = "") -> str:
    """Buat header pesan standar.

    Args:
        title: Judul utama.
        subtitle: Subjudul opsional.

    Returns:
        String HTML header.
    """
    text = f"<b>{escape_html(title)}</b>"
    if subtitle:
        text += f"\n<i>{escape_html(subtitle)}</i>"
    text += "\n" + "━" * 32
    return text


def build_success_message(title: str, details: str = "") -> str:
    """Template pesan sukses.

    Args:
        title: Judul tindakan yang berhasil.
        details: Detail tambahan.

    Returns:
        Pesan HTML terformat.
    """
    text = f"✅ <b>Berhasil</b>\n\n{escape_html(title)}"
    if details:
        text += f"\n\n{escape_html(details)}"
    return text


def build_error_message(title: str, reason: str = "", suggestion: str = "") -> str:
    """Template pesan error.

    Args:
        title: Judul error.
        reason: Alasan error.
        suggestion: Saran tindak lanjut.

    Returns:
        Pesan HTML terformat.
    """
    text = f"❌ <b>Gagal</b>\n\n{escape_html(title)}"
    if reason:
        text += f"\n\n<b>Alasan:</b> {escape_html(reason)}"
    if suggestion:
        text += f"\n\n<b>Saran:</b> {escape_html(suggestion)}"
    return text


def build_warning_message(title: str, body: str = "") -> str:
    """Template pesan peringatan.

    Args:
        title: Judul peringatan.
        body: Isi peringatan.

    Returns:
        Pesan HTML terformat.
    """
    text = f"⚠️ <b>Peringatan</b>\n\n{escape_html(title)}"
    if body:
        text += f"\n\n{escape_html(body)}"
    return text


def build_info_message(title: str, body: str = "") -> str:
    """Template pesan informasi.

    Args:
        title: Judul info.
        body: Isi info.

    Returns:
        Pesan HTML terformat.
    """
    text = f"ℹ️ <b>Info</b>\n\n{escape_html(title)}"
    if body:
        text += f"\n\n{escape_html(body)}"
    return text


def build_confirmation_message(
    action: str,
    description: str = "",
    warning: str = "",
) -> str:
    """Template pesan konfirmasi untuk operasi berbahaya.

    Args:
        action: Tindakan yang akan dikonfirmasi.
        description: Deskripsi dampak tindakan.
        warning: Peringatan khusus.

    Returns:
        Pesan HTML terformat untuk konfirmasi.
    """
    text = f"⚠️ <b>Konfirmasi</b>\n\n<b>{escape_html(action)}?</b>"
    if description:
        text += f"\n\n{escape_html(description)}"
    if warning:
        text += f"\n\n⚠️ <i>{escape_html(warning)}</i>"
    return text


def build_loading_message(action: str) -> str:
    """Template pesan loading.

    Args:
        action: Tindakan yang sedang diproses.

    Returns:
        Pesan HTML loading.
    """
    return f"⏳ <b>Memproses...</b>\n\n{escape_html(action)}, mohon tunggu."


def build_denied_message(reason: str = "") -> str:
    """Template pesan akses ditolak.

    Args:
        reason: Alasan penolakan.

    Returns:
        Pesan HTML akses ditolak.
    """
    text = "🚫 <b>Akses Ditolak</b>\n\nAnda tidak memiliki izin untuk perintah ini."
    if reason:
        text += f"\n\n<i>{escape_html(reason)}</i>"
    return text


def build_system_status(
    hostname: str,
    os_name: str,
    uptime_seconds: int,
    cpu_percent: float,
    cpu_cores: int,
    ram_used_bytes: int,
    ram_total_bytes: int,
    ram_percent: float,
    disk_used_bytes: int,
    disk_total_bytes: int,
    disk_percent: float,
    load1: float,
    load5: float,
    load15: float,
) -> str:
    """Bangun pesan dashboard status server lengkap.

    Returns:
        Pesan HTML status server yang terformat.
    """
    cpu_bar = make_progress_bar(cpu_percent)
    ram_bar = make_progress_bar(ram_percent)
    disk_bar = make_progress_bar(disk_percent)

    ram_used = format_bytes(ram_used_bytes)
    ram_total = format_bytes(ram_total_bytes)
    disk_used = format_bytes(disk_used_bytes)
    disk_total = format_bytes(disk_total_bytes)
    uptime = format_uptime(uptime_seconds)
    load = format_load_average(load1, load5, load15)

    return (
        f"🤖 <b>Serverinka Guardian</b>\n"
        f"🖥️ <code>{escape_html(hostname)}</code>\n"
        f"🐧 {escape_html(os_name)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱️ <b>Uptime:</b> {uptime}\n\n"
        f"<b>CPU</b>  <code>{cpu_bar}  {cpu_percent:.1f}%</code> ({cpu_cores} core)\n"
        f"<b>RAM</b>  <code>{ram_bar}  {ram_percent:.1f}%</code> ({ram_used}/{ram_total})\n"
        f"<b>Disk</b> <code>{disk_bar}  {disk_percent:.1f}%</code> ({disk_used}/{disk_total})\n"
        f"<b>Load</b> <code>{load}</code>"
    )


def build_alert_message(
    hostname: str,
    metric_name: str,
    current_value: float,
    threshold_value: float,
    unit: str,
) -> str:
    """Bangun pesan notifikasi alert.

    Args:
        hostname: Nama server.
        metric_name: Nama metrik yang terpicu.
        current_value: Nilai saat ini.
        threshold_value: Nilai threshold.
        unit: Satuan metrik.

    Returns:
        Pesan HTML alert yang terformat.
    """
    metric_display = metric_name.replace("_", " ").title()
    value_str = f"{current_value:.1f} {unit}"
    threshold_str = f"{threshold_value:.1f} {unit}"

    return (
        f"🚨 <b>ALERT — {escape_html(hostname)}</b>\n\n"
        f"<b>{metric_display} Tinggi</b>\n\n"
        f"Nilai saat ini: <code>{value_str}</code>\n"
        f"Threshold:      <code>{threshold_str}</code>"
    )


def split_long_message(text: str, max_length: int = 4000) -> list[str]:
    """Pecah pesan panjang menjadi beberapa bagian.

    Args:
        text: Teks yang mungkin terlalu panjang.
        max_length: Panjang maksimum per bagian.

    Returns:
        List bagian pesan.
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    lines = text.splitlines(keepends=True)
    current = ""

    for line in lines:
        if len(current) + len(line) > max_length:
            if current:
                parts.append(current)
            current = line
        else:
            current += line

    if current:
        parts.append(current)

    return parts
