"""Models untuk Terminal Plugin."""

from dataclasses import dataclass, field


@dataclass
class TerminalSessionDTO:
    """State sesi terminal per user."""

    user_id: int
    cwd: str
    last_active: float


@dataclass
class CommandHistoryDTO:
    """Riwayat perintah terminal."""

    id: int
    user_id: int
    command: str
    exit_code: int
    executed_at: float


@dataclass
class CommandResultDTO:
    """Hasil eksekusi perintah shell."""

    command: str
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    cwd: str = "/"
    blocked: bool = False
    block_reason: str = ""
    truncated: bool = False

    @property
    def success(self) -> bool:
        """True jika exit code 0 dan tidak timeout."""
        return self.exit_code == 0 and not self.timed_out and not self.blocked

    @property
    def combined_output(self) -> str:
        """Gabungan stdout dan stderr."""
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.rstrip())
        if self.stderr.strip():
            parts.append(f"[stderr] {self.stderr.rstrip()}")
        return "\n".join(parts) if parts else "(tidak ada output)"
