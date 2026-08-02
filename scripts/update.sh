#!/usr/bin/env bash
# =====================================================================
# SERVERINKA GUARDIAN — SCRIPT UPDATE OTOMATIS
# =====================================================================
set -euo pipefail

INSTALL_DIR="/opt/serverinka-guardian"

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Harap jalankan script ini sebagai root (sudo bash scripts/update.sh)."
    exit 1
fi

echo "[INFO] Memulai proses update Serverinka Guardian..."

# 1. Hentikan service
echo "[INFO] Menghentikan service serverinka-guardian..."
systemctl stop serverinka-guardian.service || true

# 2. Pull perubahan git terbaru
echo "[INFO] Memilih update git..."
cd "$INSTALL_DIR"
git pull origin main

# 3. Update dependensi via uv
echo "[INFO] Mengupdate dependensi..."
su - serverinka -c "cd $INSTALL_DIR && /usr/local/bin/uv sync"

# 4. Jalankan ulang service
echo "[INFO] Memulai kembali service serverinka-guardian..."
systemctl start serverinka-guardian.service

echo "[INFO] Update berhasil! Cek status via: sudo systemctl status serverinka-guardian"
