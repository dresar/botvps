"""Service bisnis untuk process_guardian plugin."""

import asyncio
import os
import re
import signal
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import psutil
import structlog

from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.process_guardian.models import (
    CPUGuardConfigDTO,
    CPUGuardHistoryDTO,
    ProcessInfoDTO,
)
from guardian.plugins.process_guardian.repository import CPUGuardRepository
from guardian.utils.formatters import escape_html, format_uptime

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)

# System Whitelist Default yang tidak boleh dihentikan
DEFAULT_SYSTEM_WHITELIST = {
    "systemd",
    "init",
    "sshd",
    "dockerd",
    "containerd",
    "nginx",
    "postgres",
    "redis-server",
    "python",
    "python3",
    "casaos",
    "casaos-gateway",
}


class ProcessGuardianService(BaseService):
    """Service pengawas dan pelindung CPU VPS dari beban ekstrim."""

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self.repo = CPUGuardRepository(ctx.db)
        self._enabled = True
        self._cooldown_cache: dict[str, float] = {}  # key -> timestamp last killed
        self._consecutive_overload_counts: dict[int, int] = {}  # PID -> count

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan service."""
        status = "healthy" if self._enabled else "degraded"
        return ServiceHealth(
            service_name="ProcessGuardianService",
            status=status,
            message="CPU Guard Monitoring Aktif." if status == "healthy" else "CPU Guard Nonaktif.",
            checked_at=datetime.utcnow(),
        )

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    async def get_top_cpu_processes(self, limit: int = 20) -> list[ProcessInfoDTO]:
        """Ambil daftar N proses dengan penggunaan CPU tertinggi."""
        def _fetch_top() -> list[ProcessInfoDTO]:
            procs = []
            for p in psutil.process_iter(
                ["pid", "name", "username", "cpu_percent", "memory_percent", "cmdline", "create_time"]
            ):
                try:
                    p_info = p.info
                    cmd = " ".join(p_info.get("cmdline") or []) or p_info.get("name", "N/A")
                    uptime_sec = time.time() - (p_info.get("create_time") or time.time())
                    procs.append(
                        ProcessInfoDTO(
                            pid=p_info["pid"],
                            name=p_info.get("name") or "unknown",
                            username=p_info.get("username") or "root",
                            cpu_percent=p_info.get("cpu_percent") or 0.0,
                            memory_percent=p_info.get("memory_percent") or 0.0,
                            cmdline=cmd,
                            running_time=format_uptime(int(uptime_sec)),
                            create_time=p_info.get("create_time") or 0.0,
                        )
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x.cpu_percent, reverse=True)
            return procs[:limit]

        return await asyncio.to_thread(_fetch_top)

    async def check_and_enforce_cpu_limits(self) -> None:
        """Pemeriksaan berkala seluruh proses terhadap ambang batas CPU."""
        if not self._enabled:
            return

        settings = self._ctx.settings
        limit = settings.cpu_usage_limit
        top_procs = await self.get_top_cpu_processes(limit=50)

        db_whitelist = set(await self.repo.get_rules("whitelist"))
        db_blacklist = set(await self.repo.get_rules("blacklist"))

        for proc in top_procs:
            if proc.cpu_percent < limit:
                self._consecutive_overload_counts.pop(proc.pid, None)
                continue

            # Increment consecutive count
            count = self._consecutive_overload_counts.get(proc.pid, 0) + 1
            self._consecutive_overload_counts[proc.pid] = count

            if self._is_whitelisted(proc, db_whitelist, db_blacklist):
                logger.debug("Proses overload tetapi masuk whitelist.", pid=proc.pid, name=proc.name)
                continue

            # Peringatan pertama jika berturut-turut
            if count == 1:
                logger.warn("High CPU Process Terdeteksi (Warning awal).", pid=proc.pid, name=proc.name, cpu=proc.cpu_percent)
                await self._notify_telegram_warning(proc, reason=f"Melewati batas CPU {limit}% ({proc.cpu_percent:.1f}%)")
                continue

            # Eksekusi penanganan (Kill / Warn Mode)
            if count >= 2:
                await self._handle_overload_process(proc, reason=f"Penggunaan CPU tinggi {proc.cpu_percent:.1f}% >= {limit}%")

    def _is_whitelisted(self, proc: ProcessInfoDTO, db_whitelist: set[str], db_blacklist: set[str]) -> bool:
        """Cek apakah proses aman (tidak boleh dibunuh)."""
        name_lower = proc.name.lower()
        cmd_lower = proc.cmdline.lower()

        # Blacklist diutamakan
        if name_lower in db_blacklist:
            return False

        # 1. Self Check: Jangan pernah bunuh bot Serverinka Guardian sendiri
        if proc.pid == os.getpid() or "guardian" in cmd_lower:
            return True

        # 2. Kernel & Process ID Krusial
        if proc.pid <= 2 or proc.name.startswith("["):
            return True

        # 3. Default & DB Whitelist
        if name_lower in DEFAULT_SYSTEM_WHITELIST or name_lower in db_whitelist:
            return True

        # 4. Whitelist via Config Ignores
        settings = self._ctx.settings
        if proc.username in settings.cpu_ignore_users:
            return True
        if name_lower in settings.cpu_ignore_process:
            return True
        if proc.pid in settings.cpu_ignore_pid:
            return True
        if settings.cpu_ignore_regex and re.search(settings.cpu_ignore_regex, cmd_lower):
            return True

        return False

    async def _handle_overload_process(self, proc: ProcessInfoDTO, reason: str) -> None:
        """Kendalikan proses overload dengan SIGTERM -> SIGKILL."""
        settings = self._ctx.settings
        cooldown_key = f"{proc.name}:{proc.pid}"
        now = time.time()

        if cooldown_key in self._cooldown_cache:
            if now - self._cooldown_cache[cooldown_key] < settings.cpu_cooldown:
                logger.debug("Proses dalam masa cooldown kill.", key=cooldown_key)
                return

        self._cooldown_cache[cooldown_key] = now

        if settings.cpu_kill_mode == "warn":
            await self._record_and_notify(proc, action="WARNING", status="success", reason=reason)
            return

        # Attempt Kill: SIGTERM terlebih dahulu
        action_taken = "SIGTERM"
        status = "success"
        killed = False

        try:
            p = psutil.Process(proc.pid)
            p.send_signal(signal.SIGTERM)
            await asyncio.sleep(settings.cpu_grace_timeout)

            if p.is_running():
                p.send_signal(signal.SIGKILL)
                action_taken = "SIGKILL"
                await asyncio.sleep(1)

            killed = not p.is_running()
        except psutil.NoSuchProcess:
            killed = True
            status = "success"
        except Exception as e:
            status = "failed"
            reason += f" (Error: {e})"

        if not killed:
            status = "failed"

        await self._record_and_notify(proc, action=action_taken, status=status, reason=reason)

    async def kill_process_by_pid(self, pid: int, admin_id: int) -> tuple[bool, str]:
        """Hentikan proses secara manual berdasarkan PID."""
        try:
            p = psutil.Process(pid)
            name = p.name()
            cmd = " ".join(p.cmdline()) or name
            proc_info = ProcessInfoDTO(
                pid=pid,
                name=name,
                username=p.username(),
                cpu_percent=p.cpu_percent(),
                memory_percent=p.memory_percent(),
                cmdline=cmd,
                running_time=format_uptime(int(time.time() - p.create_time())),
                create_time=p.create_time(),
            )
            if proc_info.pid == os.getpid() or "guardian" in cmd.lower():
                return False, "Tidak dapat menghentikan bot Serverinka Guardian sendiri!"

            p.send_signal(signal.SIGTERM)
            await asyncio.sleep(2)
            if p.is_running():
                p.send_signal(signal.SIGKILL)

            await self._record_and_notify(proc_info, action="SIGKILL (Manual)", status="success", reason=f"Killed oleh admin {admin_id}")
            return True, f"Proses <code>{escape_html(name)}</code> (PID {pid}) berhasil dihentikan."
        except psutil.NoSuchProcess:
            return False, f"Proses PID {pid} tidak ditemukan."
        except Exception as e:
            return False, f"Gagal menghentikan proses: {e}"

    async def _record_and_notify(self, proc: ProcessInfoDTO, action: str, status: str, reason: str) -> None:
        """Simpan ke DB, log audit, dan kirim notifikasi Telegram."""
        history = CPUGuardHistoryDTO(
            pid=proc.pid,
            process_name=proc.name,
            username=proc.username,
            cpu_percent=proc.cpu_percent,
            memory_percent=proc.memory_percent,
            cmdline=proc.cmdline,
            running_time=proc.running_time,
            action_taken=action,
            status=status,
            reason=reason,
            executed_at=datetime.utcnow(),
        )

        await self.repo.add_history(history)
        await self._ctx.audit_service.log_action(
            user_id=0,
            action="cpu_guard_enforce",
            details=f"Process: {proc.name} (PID {proc.pid}) Action: {action} Status: {status}",
        )

        if self._ctx.settings.cpu_notification:
            await self._notify_telegram_action(history)

    async def _notify_telegram_warning(self, proc: ProcessInfoDTO, reason: str) -> None:
        """Kirim notifikasi warning awal."""
        msg = (
            f"⚠️ <b>High CPU Process Detected</b>\n\n"
            f"<b>Proses:</b> <code>{escape_html(proc.name)}</code>\n"
            f"<b>PID:</b> <code>{proc.pid}</code> | <b>User:</b> <code>{escape_html(proc.username)}</code>\n"
            f"<b>CPU:</b> <code>{proc.cpu_percent:.1f}%</code> | <b>RAM:</b> <code>{proc.memory_percent:.1f}%</code>\n"
            f"<b>Running Time:</b> <code>{proc.running_time}</code>\n"
            f"<b>Command:</b> <code>{escape_html(proc.cmdline[:120])}</code>\n\n"
            f"<b>Status:</b> Peringatan awal (menunggu tindakan)."
        )
        await self._broadcast_admin(msg)

    async def _notify_telegram_action(self, history: CPUGuardHistoryDTO) -> None:
        """Kirim notifikasi tindakan kill/warn."""
        status_icon = "✅" if history.status == "success" else "❌"
        msg = (
            f"🛑 <b>CPU Guard Action Executed</b>\n\n"
            f"<b>Nama Proses:</b> <code>{escape_html(history.process_name)}</code>\n"
            f"<b>PID:</b> <code>{history.pid}</code> | <b>User:</b> <code>{escape_html(history.username)}</code>\n"
            f"<b>CPU:</b> <code>{history.cpu_percent:.1f}%</code> | <b>RAM:</b> <code>{history.memory_percent:.1f}%</code>\n"
            f"<b>Running Time:</b> <code>{history.running_time}</code>\n"
            f"<b>Command:</b> <code>{escape_html(history.cmdline[:120])}</code>\n\n"
            f"<b>Tindakan:</b> <code>{history.action_taken}</code>\n"
            f"<b>Alasan:</b> <i>{escape_html(history.reason)}</i>\n"
            f"<b>Status:</b> {status_icon} <b>{history.status.upper()}</b>"
        )
        await self._broadcast_admin(msg)

    async def _broadcast_admin(self, msg: str) -> None:
        """Kirim pesan ke seluruh admin."""
        try:
            admin_ids = await self._ctx.auth.get_all_alert_recipient_ids()
            if admin_ids:
                await self._ctx.bot_gateway.broadcast(admin_ids, msg)
        except Exception:
            logger.warning("Gagal mengirim notifikasi CPU Guard ke Telegram.")

    async def get_config_summary(self) -> CPUGuardConfigDTO:
        """Ambil ringkasan status & konfigurasi."""
        w = await self.repo.get_rules("whitelist")
        b = await self.repo.get_rules("blacklist")
        s = self._ctx.settings
        return CPUGuardConfigDTO(
            enabled=self._enabled,
            limit_percent=s.cpu_usage_limit,
            check_interval_seconds=s.cpu_check_interval,
            grace_timeout_seconds=s.cpu_grace_timeout,
            kill_mode=s.cpu_kill_mode,
            notification_enabled=s.cpu_notification,
            cooldown_seconds=s.cpu_cooldown,
            whitelist=list(DEFAULT_SYSTEM_WHITELIST.union(w)),
            blacklist=b,
        )
