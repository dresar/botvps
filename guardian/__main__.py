"""Entry point untuk Serverinka Guardian."""

import asyncio
import logging
import sys

import structlog

from guardian.core.engine import GuardianEngine


def _configure_logging(log_level: str) -> None:
    """Konfigurasi structlog untuk output yang konsisten."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )


def main() -> None:
    """Fungsi entry point utama."""
    from guardian.core.config import get_settings

    try:
        settings = get_settings()
    except Exception as e:
        print(f"[FATAL] Gagal memuat konfigurasi: {e}", file=sys.stderr)
        print("Pastikan file .env sudah dikonfigurasi dengan benar.", file=sys.stderr)
        sys.exit(1)

    _configure_logging(settings.log_level)

    log = structlog.get_logger("guardian.main")
    log.info("Serverinka Guardian memulai...", version="1.0.0")

    engine = GuardianEngine(settings)

    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        log.info("Bot dihentikan oleh pengguna (KeyboardInterrupt).")
    except Exception as e:
        log.exception("Bot berhenti karena error kritis.", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
