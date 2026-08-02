"""Subprocess sandbox yang aman — tidak menggunakan shell=True."""

import asyncio
import shlex
from dataclasses import dataclass

import structlog

from guardian.core.exceptions import CommandExecutionError

logger = structlog.get_logger(__name__)

DEFAULT_TIMEOUT = 30.0
MAX_OUTPUT_BYTES = 512 * 1024  # 512 KB


@dataclass
class CommandResult:
    """Hasil eksekusi perintah subprocess."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """True jika returncode == 0 dan tidak timeout."""
        return self.returncode == 0 and not self.timed_out


async def run_command(
    command: list[str],
    timeout: float = DEFAULT_TIMEOUT,
    input_data: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Jalankan perintah sistem secara async dengan sandbox.

    Menggunakan asyncio.create_subprocess_exec (bukan shell=True)
    untuk mencegah shell injection.

    Args:
        command: List perintah dan argumen. JANGAN gunakan string shell.
        timeout: Timeout dalam detik.
        input_data: Data stdin opsional.
        cwd: Working directory untuk perintah.

    Returns:
        CommandResult dengan output dan return code.

    Raises:
        CommandExecutionError: Jika perintah tidak ditemukan atau timeout.

    Example:
        result = await run_command(["systemctl", "status", "nginx.service"])
    """
    if not command:
        raise CommandExecutionError("Command tidak boleh kosong.")

    log = logger.bind(command=shlex.join(command))

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if input_data else None,
            cwd=cwd,
        )
    except FileNotFoundError as e:
        raise CommandExecutionError(
            f"Perintah tidak ditemukan: {command[0]}",
            detail=str(e),
        ) from e
    except PermissionError as e:
        raise CommandExecutionError(
            f"Tidak ada izin untuk menjalankan: {command[0]}",
            detail=str(e),
        ) from e

    try:
        stdin_bytes = input_data.encode() if input_data else None
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=stdin_bytes),
            timeout=timeout,
        )
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        log.warning("Command timeout.", timeout=timeout)
        return CommandResult(
            returncode=-1,
            stdout="",
            stderr=f"Timeout setelah {timeout} detik.",
            timed_out=True,
        )

    stdout = stdout_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    stderr = stderr_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

    log.debug(
        "Command selesai.",
        returncode=proc.returncode,
        stdout_len=len(stdout),
        stderr_len=len(stderr),
    )

    return CommandResult(
        returncode=proc.returncode or 0,
        stdout=stdout,
        stderr=stderr,
    )


async def run_command_streaming(
    command: list[str],
    timeout: float = 120.0,
    cwd: str | None = None,
) -> asyncio.subprocess.Process:
    """Jalankan perintah dengan output streaming.

    Args:
        command: List perintah dan argumen.
        timeout: Timeout untuk startup.
        cwd: Working directory.

    Returns:
        Process object untuk membaca output secara streaming.

    Raises:
        CommandExecutionError: Jika perintah tidak dapat dijalankan.
    """
    if not command:
        raise CommandExecutionError("Command tidak boleh kosong.")

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        return proc
    except FileNotFoundError as e:
        raise CommandExecutionError(
            f"Perintah tidak ditemukan: {command[0]}",
            detail=str(e),
        ) from e
