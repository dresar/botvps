"""Validator untuk input pengguna dari Telegram bot."""

import re


_SERVICE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.@]{1,256}$")
_CONTAINER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,127}$")
_CRON_PATTERN = re.compile(
    r"^(\*|[0-9]{1,2}(-[0-9]{1,2})?(,[0-9]{1,2}(-[0-9]{1,2})?)*)\s+"
    r"(\*|[0-9]{1,2}(-[0-9]{1,2})?(,[0-9]{1,2}(-[0-9]{1,2})?)*)\s+"
    r"(\*|[0-9]{1,2}(-[0-9]{1,2})?(,[0-9]{1,2}(-[0-9]{1,2})?)*)\s+"
    r"(\*|[0-9]{1,2}(-[0-9]{1,2})?(,[0-9]{1,2}(-[0-9]{1,2})?)*)\s+"
    r"(\*|[0-9]{1,2}(-[0-9]{1,2})?(,[0-9]{1,2}(-[0-9]{1,2})?)*)$"
)

VALID_ROLES = frozenset({"super_admin", "admin", "operator", "viewer"})

DANGEROUS_SERVICES = frozenset({
    "serverinka-guardian",
    "sshd",
    "ssh",
    "systemd",
    "systemd-journald",
    "systemd-udevd",
    "dbus",
    "init",
})


def is_valid_service_name(name: str) -> bool:
    """Validasi nama layanan systemd.

    Args:
        name: Nama layanan yang akan divalidasi.

    Returns:
        True jika valid, False jika tidak.
    """
    if not name or len(name) > 256:
        return False
    return bool(_SERVICE_NAME_PATTERN.match(name))


def is_dangerous_service(name: str) -> bool:
    """Cek apakah layanan termasuk dalam daftar layanan yang tidak boleh diubah.

    Args:
        name: Nama layanan.

    Returns:
        True jika layanan berbahaya untuk dimodifikasi.
    """
    base_name = name.replace(".service", "")
    return base_name in DANGEROUS_SERVICES or name in DANGEROUS_SERVICES


def is_valid_container_name(name: str) -> bool:
    """Validasi nama kontainer Docker.

    Args:
        name: Nama kontainer yang akan divalidasi.

    Returns:
        True jika valid, False jika tidak.
    """
    if not name or len(name) > 128:
        return False
    return bool(_CONTAINER_NAME_PATTERN.match(name))


def is_valid_pid(pid_str: str) -> bool:
    """Validasi bahwa string adalah PID yang valid.

    Args:
        pid_str: String yang akan divalidasi sebagai PID.

    Returns:
        True jika merupakan integer positif yang valid.
    """
    try:
        pid = int(pid_str)
        return pid > 0
    except (ValueError, TypeError):
        return False


def is_valid_telegram_id(user_id_str: str) -> bool:
    """Validasi bahwa string adalah Telegram User ID yang valid.

    Args:
        user_id_str: String yang akan divalidasi.

    Returns:
        True jika merupakan integer positif.
    """
    try:
        uid = int(user_id_str)
        return uid > 0
    except (ValueError, TypeError):
        return False


def is_valid_role(role: str) -> bool:
    """Validasi bahwa role adalah salah satu role yang valid.

    Args:
        role: Nama role yang akan divalidasi.

    Returns:
        True jika role valid.
    """
    return role in VALID_ROLES


def is_valid_cron_expression(expression: str) -> bool:
    """Validasi dasar untuk ekspresi cron (5 field).

    Args:
        expression: Ekspresi cron yang akan divalidasi.

    Returns:
        True jika format ekspresi cron valid.
    """
    return bool(_CRON_PATTERN.match(expression.strip()))


def sanitize_log_output(text: str, max_length: int = 4000) -> str:
    """Sanitasi output log untuk ditampilkan di Telegram.

    Menghapus karakter kontrol dan membatasi panjang.

    Args:
        text: Teks output log.
        max_length: Panjang maksimum output.

    Returns:
        Teks yang sudah disanitasi.
    """
    clean = text.replace("\r\n", "\n").replace("\r", "\n")
    clean = "".join(c for c in clean if c.isprintable() or c == "\n")
    if len(clean) > max_length:
        lines = clean.splitlines()
        while len("\n".join(lines)) > max_length and lines:
            lines.pop(0)
        clean = "\n".join(lines)
        if len(clean) > max_length:
            clean = "..." + clean[-(max_length - 3):]
    return clean
