"""Service bisnis untuk Terminal Plugin — eksekusi command & manajemen sesi."""

import asyncio
import re
import shlex
import time
from typing import TYPE_CHECKING

import structlog

from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.terminal.models import CommandResultDTO, TerminalSessionDTO
from guardian.plugins.terminal.repository import TerminalRepository
from guardian.utils.sandbox import run_command

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)

DEFAULT_CWD = "/"
COMMAND_TIMEOUT = 30.0
MAX_OUTPUT_CHARS = 3500  # Telegram max 4096, sisakan ruang untuk header
SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 menit

# ---------------------------------------------------------------------------
# Pola Perintah Berbahaya (Danger Guard)
# ---------------------------------------------------------------------------
_DANGER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\b.{0,20}-[a-zA-Z]*r[a-zA-Z]*.{0,10}/\s*$", re.IGNORECASE),
    re.compile(r"\bdd\b.+\bif=/dev/(zero|random|urandom)\b.+\bof=/dev/[a-z]+", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bwipefs\b", re.IGNORECASE),
    re.compile(r">\s*/dev/(sda|sdb|sdc|sdd|nvme)", re.IGNORECASE),
    re.compile(r"\bchmod\s+-R\s+[0-7]{3,4}\s+/\s*$", re.IGNORECASE),
    re.compile(r":\(\)\s*\{", re.IGNORECASE),   # fork bomb
    re.compile(r"\bshutdown\b.+\b-h\b", re.IGNORECASE),
    re.compile(r"\bpoweroff\b", re.IGNORECASE),
    re.compile(r"\bhalt\b", re.IGNORECASE),
    re.compile(r"\bsudo\s+rm\b.{0,20}/\s*$", re.IGNORECASE),
]

# Perintah yang harus ditangani secara khusus (bukan via subprocess)
_BUILTIN_CD = re.compile(r"^\s*cd(\s+.+)?\s*$")
_BUILTIN_CLEAR = re.compile(r"^\s*(clear|cls)\s*$")
_BUILTIN_HISTORY = re.compile(r"^\s*history\s*$")
_BUILTIN_EXIT = re.compile(r"^\s*(exit|quit|logout)\s*$")
_BUILTIN_PWD = re.compile(r"^\s*pwd\s*$")


class TerminalService(BaseService):
    """Service untuk mengelola eksekusi perintah shell dan sesi terminal."""

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self.repo = TerminalRepository(ctx.database)

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan service."""
        from datetime import datetime
        return ServiceHealth(
            service_name="TerminalService",
            status="healthy",
            message="Terminal Plugin siap menerima perintah.",
            checked_at=datetime.utcnow(),
        )

    # ---------------------------------------------------------------------- session

    async def get_or_create_session(self, user_id: int) -> TerminalSessionDTO:
        """Ambil sesi aktif atau buat sesi baru."""
        session = await self.repo.get_session(user_id)
        if session is None:
            await self.repo.upsert_session(user_id, DEFAULT_CWD)
            session = TerminalSessionDTO(user_id=user_id, cwd=DEFAULT_CWD, last_active=time.time())
            return session

        # Reset sesi jika sudah kadaluarsa
        idle_seconds = time.time() - session.last_active
        if idle_seconds > SESSION_TIMEOUT_SECONDS:
            await self.repo.upsert_session(user_id, DEFAULT_CWD)
            session = TerminalSessionDTO(user_id=user_id, cwd=DEFAULT_CWD, last_active=time.time())
        return session

    async def reset_session(self, user_id: int) -> None:
        """Reset sesi user ke direktori default."""
        await self.repo.delete_session(user_id)

    # ---------------------------------------------------------------- danger guard

    def is_dangerous(self, raw_cmd: str) -> tuple[bool, str]:
        """Cek apakah perintah masuk daftar blacklist berbahaya.

        Returns:
            (is_dangerous, reason)
        """
        for pattern in _DANGER_PATTERNS:
            if pattern.search(raw_cmd):
                return True, f"Perintah cocok dengan pola berbahaya: `{pattern.pattern}`"
        return False, ""

    # --------------------------------------------------------------- built-ins

    async def handle_builtin(
        self, raw_cmd: str, session: TerminalSessionDTO
    ) -> CommandResultDTO | None:
        """Tangani perintah built-in shell (cd, pwd, clear, dll).

        Returns:
            CommandResultDTO jika perintah adalah built-in, None jika bukan.
        """
        cmd_stripped = raw_cmd.strip()

        # pwd
        if _BUILTIN_PWD.match(cmd_stripped):
            return CommandResultDTO(
                command=raw_cmd, stdout=session.cwd, stderr="", exit_code=0, cwd=session.cwd
            )

        # clear / cls
        if _BUILTIN_CLEAR.match(cmd_stripped):
            return CommandResultDTO(
                command=raw_cmd,
                stdout="🖥️ Terminal dibersihkan.",
                stderr="",
                exit_code=0,
                cwd=session.cwd,
            )

        # exit / quit
        if _BUILTIN_EXIT.match(cmd_stripped):
            return CommandResultDTO(
                command=raw_cmd,
                stdout="👋 Session terminal tetap aktif. Gunakan /terminal reset untuk mereset session.",
                stderr="",
                exit_code=0,
                cwd=session.cwd,
            )

        # cd <path>
        if _BUILTIN_CD.match(cmd_stripped):
            parts = cmd_stripped.split(None, 1)
            target = parts[1].strip() if len(parts) > 1 else "/root"

            # Resolve path relatif
            if not target.startswith("/"):
                import os
                target = os.path.normpath(f"{session.cwd}/{target}")

            # Verifikasi direktori ada (via subprocess singkat)
            verify = await run_command(["test", "-d", target], timeout=5.0)
            if not verify.success:
                return CommandResultDTO(
                    command=raw_cmd,
                    stdout="",
                    stderr=f"cd: {target}: No such file or directory",
                    exit_code=1,
                    cwd=session.cwd,
                )
            await self.repo.upsert_session(session.user_id, target)
            session.cwd = target
            return CommandResultDTO(
                command=raw_cmd, stdout=f"📂 Pindah ke: {target}", stderr="", exit_code=0, cwd=target
            )

        return None

    # ------------------------------------------------------------------ execute

    async def execute(self, user_id: int, raw_cmd: str) -> CommandResultDTO:
        """Eksekusi perintah shell di VPS.

        Args:
            user_id: ID user Telegram yang menjalankan perintah.
            raw_cmd: String perintah mentah dari user.

        Returns:
            CommandResultDTO dengan output dan metadata.
        """
        raw_cmd = raw_cmd.strip()
        if not raw_cmd:
            return CommandResultDTO(
                command="", stdout="", stderr="Perintah kosong.", exit_code=1, cwd=DEFAULT_CWD
            )

        # Dapatkan / buat sesi
        session = await self.get_or_create_session(user_id)

        # Cek danger guard
        settings = self._ctx.settings
        if getattr(settings, "terminal_danger_guard", True):
            dangerous, reason = self.is_dangerous(raw_cmd)
            if dangerous:
                logger.warning("🚨 [TERMINAL DANGER GUARD] Perintah diblokir.", cmd=raw_cmd, reason=reason)
                return CommandResultDTO(
                    command=raw_cmd,
                    stdout="",
                    stderr="",
                    exit_code=127,
                    cwd=session.cwd,
                    blocked=True,
                    block_reason=reason,
                )

        # Handle built-in (cd, pwd, clear)
        builtin_result = await self.handle_builtin(raw_cmd, session)
        if builtin_result is not None:
            await self.repo.save_history(user_id, raw_cmd, builtin_result.exit_code)
            return builtin_result

        # Parsing & eksekusi via subprocess (tanpa shell=True)
        try:
            cmd_tokens = shlex.split(raw_cmd)
        except ValueError as e:
            return CommandResultDTO(
                command=raw_cmd, stdout="", stderr=f"Parse error: {e}", exit_code=1, cwd=session.cwd
            )

        max_kb = getattr(settings, "terminal_max_output_kb", 10)
        timeout = getattr(settings, "terminal_command_timeout", COMMAND_TIMEOUT)

        logger.info(
            "💻 [TERMINAL EXEC]",
            user_id=user_id,
            cmd=raw_cmd,
            cwd=session.cwd,
        )

        result = await run_command(cmd_tokens, timeout=float(timeout), cwd=session.cwd)

        # Gabungkan output
        stdout = result.stdout
        stderr = result.stderr
        truncated = False

        # Potong jika terlalu panjang
        max_chars = max_kb * 1024
        combined = stdout + ("\n" + stderr if stderr.strip() else "")
        if len(combined) > max_chars:
            stdout = combined[:max_chars]
            stderr = ""
            truncated = True

        # Simpan ke history
        await self.repo.save_history(user_id, raw_cmd, result.returncode)

        return CommandResultDTO(
            command=raw_cmd,
            stdout=stdout,
            stderr=stderr,
            exit_code=result.returncode,
            timed_out=result.timed_out,
            cwd=session.cwd,
            truncated=truncated,
        )
