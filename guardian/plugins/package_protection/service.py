"""Service bisnis untuk package_protection plugin."""

import asyncio
import os
import shutil
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
import structlog

from guardian.interfaces.base_service import BaseService, ServiceHealth
from guardian.plugins.package_protection.models import UninstallReportDTO
from guardian.plugins.package_protection.repository import PackageProtectionRepository
from guardian.utils.formatters import escape_html

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)


class PackageProtectionService(BaseService):
    """Service proteksi VPS dari aplikasi terlarang (seperti OpenCode)."""

    def __init__(self, ctx: "ApplicationContext") -> None:
        super().__init__(ctx)
        self.repo = PackageProtectionRepository(ctx.database)
        self._enabled = True

    async def health_check(self) -> ServiceHealth:
        """Cek kesehatan service."""
        status = "healthy" if self._enabled else "degraded"
        return ServiceHealth(
            service_name="PackageProtectionService",
            status=status,
            message="Package Protection Monitoring Aktif." if status == "healthy" else "Package Protection Nonaktif.",
            checked_at=datetime.utcnow(),
        )

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    async def run_full_scan(self) -> list[UninstallReportDTO]:
        """Jalankan pemindaian penuh terhadap proses, binary, folder, dan instalasi terlarang."""
        if not self._enabled:
            return []

        blocked_pkgs = await self.repo.get_blocked_packages()
        if "opencode" not in blocked_pkgs:
            blocked_pkgs.append("opencode")

        reports = []
        for pkg in blocked_pkgs:
            # 1. Cek & Kill Proses Terlarang
            await self._check_and_kill_blocked_processes(pkg)

            # 2. Cek & Batalkan Perintah Instalasi Terlarang
            await self._check_and_prevent_installations(pkg)

            # 3. Cek File System, Folder, & Binary
            report = await self._scan_and_cleanup_package(pkg)
            if report:
                reports.append(report)

        return reports

    async def _check_and_kill_blocked_processes(self, pkg_name: str) -> None:
        """Hentikan proses yang berjalan untuk paket terlarang."""
        def _scan_procs() -> list[psutil.Process]:
            matched = []
            for p in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    p_name = (p.info.get("name") or "").lower()
                    cmd = " ".join(p.info.get("cmdline") or []).lower()
                    if pkg_name in p_name or pkg_name in cmd:
                        # Abaikan bot guardian sendiri
                        if p.pid == os.getpid() or "guardian" in cmd:
                            continue
                        matched.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return matched

        procs = await asyncio.to_thread(_scan_procs)
        for p in procs:
            try:
                p.send_signal(signal.SIGTERM)
                await asyncio.sleep(2)
                if p.is_running():
                    p.send_signal(signal.SIGKILL)
                logger.info("Proses paket terlarang dihentikan.", pid=p.pid, pkg=pkg_name)
            except Exception:
                pass

    async def _check_and_prevent_installations(self, pkg_name: str) -> None:
        """Deteksi & batalkan perintah instalasi paket terlarang (curl, npm, pip, apt, dll)."""
        install_cmds = ["curl", "wget", "npm", "pip", "snap", "apt", "docker", "bash", "sh"]

        def _scan_installers() -> list[psutil.Process]:
            to_kill = []
            for p in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmd = " ".join(p.info.get("cmdline") or []).lower()
                    if any(installer in cmd for installer in install_cmds) and pkg_name in cmd:
                        if p.pid != os.getpid():
                            to_kill.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return to_kill

        installers = await asyncio.to_thread(_scan_installers)
        for p in installers:
            try:
                p.send_signal(signal.SIGKILL)
                logger.warning("Instalasi paket terlarang dibatalkan!", pid=p.pid, cmd=p.info.get("cmdline"))
                await self._broadcast_admin(
                    f"⛔ <b>Percobaan Instalasi Dibatalkan!</b>\n\n"
                    f"<b>Package:</b> <code>{pkg_name}</code>\n"
                    f"<b>Command:</b> <code>{' '.join(p.info.get('cmdline') or [])}</code>\n"
                    f"<b>Status:</b> Dihentikan paksa (SIGKILL)."
                )
            except Exception:
                pass

    async def _scan_and_cleanup_package(self, pkg_name: str) -> UninstallReportDTO | None:
        """Bersihkan binary, folder config, cache, service, dan symlink paket terlarang (termasuk npm/pip)."""
        from guardian.utils.sandbox import run_command

        home = os.path.expanduser("~")
        pkg_variants = [pkg_name]
        if not pkg_name.endswith("-ai"):
            pkg_variants.append(f"{pkg_name}-ai")

        found_binaries = []
        found_configs = []

        # 0. Coba uninstall via npm & pip HANYA jika file/binary terdeteksi ada di sistem
        for variant in pkg_variants:
            has_files = (
                shutil.which(variant) is not None
                or (Path(home) / f".{variant}").exists()
                or (Path("/root") / f".{variant}").exists()
                or (Path(home) / ".config" / variant).exists()
            )
            if not has_files:
                continue

            if shutil.which("npm"):
                try:
                    res = await run_command(["npm", "uninstall", "-g", variant], timeout=10.0)
                    if res.success and ("uninstalled" in res.stdout.lower() or "removed" in res.stdout.lower()):
                        found_configs.append(f"npm global package: {variant}")
                except Exception:
                    pass

            if shutil.which("pip") or shutil.which("pip3"):
                pip_cmd = "pip3" if shutil.which("pip3") else "pip"
                try:
                    res = await run_command([pip_cmd, "uninstall", "-y", variant], timeout=10.0)
                    if res.success and "uninstalled" in res.stdout.lower():
                        found_configs.append(f"pip package: {variant}")
                except Exception:
                    pass

        # 1. Hapus Binaries & Symlinks
        binary_locations = []
        for variant in pkg_variants:
            binary_locations.extend([
                shutil.which(variant),
                f"/usr/local/bin/{variant}",
                f"/usr/bin/{variant}",
                f"/bin/{variant}",
                f"{home}/.local/bin/{variant}",
                f"/root/.local/bin/{variant}",
            ])

        for bin_path in set(filter(None, binary_locations)):
            p = Path(bin_path)
            try:
                exists_or_symlink = p.is_symlink() or p.exists()
            except (PermissionError, OSError):
                exists_or_symlink = False

            if exists_or_symlink:
                try:
                    p.unlink(missing_ok=True)
                    found_binaries.append(str(p))
                    logger.info("Binary paket terlarang dihapus.", path=str(p))
                except Exception as e:
                    logger.error("Gagal menghapus binary.", path=str(p), error=str(e))

        # 2. Hapus Directories (Config/Cache/Data)
        targets_dir = []
        for variant in pkg_variants:
            targets_dir.extend([
                Path(home) / f".{variant}",
                Path("/root") / f".{variant}",
                Path(home) / ".config" / variant,
                Path("/root") / ".config" / variant,
                Path(home) / ".cache" / variant,
                Path(home) / ".local" / "share" / variant,
                Path("/etc") / variant,
                Path("/var/log") / variant,
            ])

        for target_dir in targets_dir:
            try:
                dir_exists = target_dir.exists()
            except (PermissionError, OSError):
                dir_exists = False

            if dir_exists:
                try:
                    if target_dir.is_dir():
                        shutil.rmtree(target_dir, ignore_errors=True)
                    else:
                        target_dir.unlink(missing_ok=True)
                    found_configs.append(str(target_dir))
                    logger.info("Folder konfigurasi/cache terlarang dihapus.", path=str(target_dir))
                except Exception as e:
                    logger.error("Gagal menghapus folder.", path=str(target_dir), error=str(e))

        if not found_binaries and not found_configs:
            return None

        # 3. Verifikasi ketersediaan command
        is_still_available = any(shutil.which(v) is not None for v in pkg_variants)
        status = "failed" if is_still_available else "success"
        details = (
            f"Paket {pkg_name} terdeteksi dan dibersihkan dari VPS. "
            f"Binary dihapus: {len(found_binaries)}, Folder/Package dihapus: {len(found_configs)}."
        )

        report = UninstallReportDTO(
            package_name=pkg_name,
            install_method="auto_detected",
            binary_location=", ".join(found_binaries) or "None",
            config_location=", ".join(found_configs) or "None",
            cache_location="Cleaned",
            status=status,
            details=details,
            executed_at=datetime.utcnow(),
        )

        await self.repo.add_report(report)
        await self._ctx.audit_service.log_action(
            user_id=0,
            action="package_guard_uninstall",
            details=f"Package: {pkg_name} Status: {status} Details: {details}",
        )
        await self._notify_telegram_uninstall(report)
        return report

    async def uninstall_package_manual(self, pkg_name: str) -> tuple[bool, str]:
        """Lakukan uninstall manual terhadap paket tertentu."""
        report = await self._scan_and_cleanup_package(pkg_name.lower().strip())
        if report:
            return True, f"✅ Paket <code>{escape_html(pkg_name)}</code> berhasil di-uninstall dan dibersihkan."
        return False, f"ℹ️ Tidak ditemukan Jejak/Binary/Config untuk paket <code>{escape_html(pkg_name)}</code>."

    async def _notify_telegram_uninstall(self, report: UninstallReportDTO) -> None:
        """Kirim notifikasi laporan uninstall ke Telegram admin."""
        status_icon = "✅" if report.status == "success" else "❌"
        msg = (
            f"🛡️ <b>Package Protection Executed</b>\n\n"
            f"<b>Nama Package:</b> <code>{escape_html(report.package_name)}</code>\n"
            f"<b>Metode Instalasi:</b> <code>{report.install_method}</code>\n"
            f"<b>Lokasi Binary:</b> <code>{escape_html(report.binary_location)}</code>\n"
            f"<b>Lokasi Config/Cache:</b> <code>{escape_html(report.config_location)}</code>\n\n"
            f"<b>Status Uninstall:</b> {status_icon} <b>{report.status.upper()}</b>\n"
            f"<b>Detail:</b> <i>{escape_html(report.details)}</i>"
        )
        await self._broadcast_admin(msg)

    async def _broadcast_admin(self, msg: str) -> None:
        """Broadcast pesan ke admin."""
        try:
            admin_ids = await self._ctx.auth.get_all_alert_recipient_ids()
            if admin_ids:
                await self._ctx.bot_gateway.broadcast(admin_ids, msg)
        except Exception:
            logger.warning("Gagal mengirim notifikasi Package Protection ke Telegram.")
