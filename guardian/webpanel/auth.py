"""Telegram initData verifier untuk Web Panel auth."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, unquote

import structlog

logger = structlog.get_logger(__name__)

MAX_AGE_SECONDS = 3600  # Tolak initData lebih dari 1 jam


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """Verifikasi Telegram WebApp initData menggunakan HMAC-SHA256.

    Ref: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Args:
        init_data: String initData dari Telegram.WebApp.initData
        bot_token: Token bot Telegram untuk HMAC key derivation

    Returns:
        Dict berisi data user yang terverifikasi, atau None jika tidak valid.
    """
    if not init_data or not bot_token:
        return None

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        # Cek umur data
        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > MAX_AGE_SECONDS:
            logger.warning("initData sudah kadaluarsa.", age=time.time() - auth_date)
            return None

        # Buat data_check_string (key=value diurutkan, dipisah \n)
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        # Derive secret key dari bot token
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()

        # Hitung expected hash
        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            logger.warning("Hash initData tidak valid.")
            return None

        # Parse user data
        user_str = parsed.get("user", "{}")
        user_data = json.loads(unquote(user_str))
        return user_data

    except Exception as e:
        logger.warning("Gagal memverifikasi initData.", error=str(e))
        return None


def extract_user_id(init_data: str, bot_token: str) -> int | None:
    """Ekstrak user_id dari initData yang sudah diverifikasi.

    Returns:
        Telegram user ID atau None jika verifikasi gagal.
    """
    user_data = verify_telegram_init_data(init_data, bot_token)
    if not user_data:
        return None
    uid = user_data.get("id")
    return int(uid) if uid else None
