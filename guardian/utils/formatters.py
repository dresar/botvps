"""Utility functions untuk formatting data sistem."""

import math


def format_bytes(num_bytes: int, precision: int = 1) -> str:
    """Format byte ke representasi yang mudah dibaca manusia.

    Args:
        num_bytes: Jumlah byte.
        precision: Jumlah desimal.

    Returns:
        String terformat, misal "1.5 GB" atau "512.0 MB".
    """
    if num_bytes < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    if num_bytes == 0:
        return "0 B"

    idx = min(int(math.floor(math.log(num_bytes, 1024))), len(units) - 1)
    value = num_bytes / (1024.0**idx)
    return f"{value:.{precision}f} {units[idx]}"


def format_uptime(seconds: int) -> str:
    """Format detik menjadi representasi uptime yang mudah dibaca.

    Args:
        seconds: Jumlah detik uptime.

    Returns:
        String terformat, misal "3 hari 14 jam 22 menit" atau "45 menit 3 detik".
    """
    if seconds < 0:
        seconds = 0

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0:
        parts.append(f"{minutes} menit")
    if secs > 0 or not parts:
        parts.append(f"{secs} detik")

    return " ".join(parts)


def format_uptime_short(seconds: int) -> str:
    """Format detik menjadi uptime ringkas.

    Args:
        seconds: Jumlah detik uptime.

    Returns:
        String ringkas, misal "3d 14h" atau "45m".
    """
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def make_progress_bar(percent: float, width: int = 10) -> str:
    """Buat progress bar berbasis karakter Unicode.

    Args:
        percent: Persentase 0-100.
        width: Lebar bar dalam karakter.

    Returns:
        String progress bar, misal "████████░░".
    """
    percent = max(0.0, min(100.0, percent))
    filled = round(percent / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def format_percent(value: float, decimal: int = 1) -> str:
    """Format nilai float sebagai persentase.

    Args:
        value: Nilai 0-100.
        decimal: Jumlah desimal.

    Returns:
        String persentase, misal "82.5%".
    """
    return f"{value:.{decimal}f}%"


def escape_html(text: str) -> str:
    """Escape karakter HTML dalam teks.

    Args:
        text: Teks yang akan di-escape.

    Returns:
        Teks dengan karakter HTML yang sudah di-escape.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Potong teks jika melebihi panjang maksimum.

    Args:
        text: Teks yang akan dipotong.
        max_length: Panjang maksimum.
        suffix: Suffix yang ditambahkan jika dipotong.

    Returns:
        Teks yang sudah dipotong jika perlu.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_load_average(load1: float, load5: float, load15: float) -> str:
    """Format load average dalam format standar.

    Args:
        load1: Load average 1 menit.
        load5: Load average 5 menit.
        load15: Load average 15 menit.

    Returns:
        String format "1.23 | 0.98 | 0.75".
    """
    return f"{load1:.2f} | {load5:.2f} | {load15:.2f}"


def format_network_speed(bytes_per_sec: float) -> str:
    """Format kecepatan jaringan.

    Args:
        bytes_per_sec: Kecepatan dalam byte per detik.

    Returns:
        String terformat, misal "1.5 MB/s".
    """
    return f"{format_bytes(int(bytes_per_sec))}/s"
