#!/usr/bin/env bash
# =====================================================================
# SERVERINKA GUARDIAN — SCRIPT SETUP AUTOMATIS (DEBIAN / UBUNTU)
# =====================================================================
set -euo pipefail

# Warna output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pastikan dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then
    log_error "Harap jalankan script ini sebagai root (sudo bash scripts/setup.sh)."
    exit 1
fi

log_info "Memulai instalasi Serverinka Guardian..."

# 1. Update paket & install dependencies dasar
log_info "Mengupdate paket sistem..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv curl git systemd

# 2. Install uv (package manager)
if ! command -v uv &> /dev/null; then
    log_info "Menginstall uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    cp "$HOME/.local/bin/uv" /usr/local/bin/uv || true
    cp "$HOME/.local/bin/uvx" /usr/local/bin/uvx || true
fi

# 3. Buat user sistem 'serverinka' jika belum ada
if ! id -u serverinka &>/dev/null; then
    log_info "Membuat user sistem 'serverinka'..."
    useradd -r -m -s /bin/bash serverinka
fi

# 4. Direktori aplikasi
INSTALL_DIR="/opt/serverinka-guardian"
CONFIG_DIR="/etc/serverinka"
VAR_DIR="/var/lib/serverinka"
LOG_DIR="/var/log/serverinka"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$VAR_DIR" "$LOG_DIR"

CURRENT_DIR="$(pwd -P)"
TARGET_DIR="$(cd "$INSTALL_DIR" && pwd -P)"

if [ "$CURRENT_DIR" != "$TARGET_DIR" ]; then
    log_info "Menyalin file aplikasi ke $INSTALL_DIR..."
    cp -r . "$INSTALL_DIR/"
fi
chown -R serverinka:serverinka "$INSTALL_DIR" "$CONFIG_DIR" "$VAR_DIR" "$LOG_DIR"
git config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true

# 5. Modifikasi Sudoers
if [ -f "$INSTALL_DIR/scripts/sudoers.d/serverinka" ]; then
    log_info "Mengkonfigurasi sudoers rules..."
    cp "$INSTALL_DIR/scripts/sudoers.d/serverinka" /etc/sudoers.d/serverinka
    chmod 0440 /etc/sudoers.d/serverinka
fi

# 6. Install dependencies Python via uv sebagai user serverinka
log_info "Menginstall dependensi Python..."
su - serverinka -c "cd $INSTALL_DIR && /usr/local/bin/uv sync"

# 7. Konfigurasi file environment
if [ ! -f "$CONFIG_DIR/guardian.env" ]; then
    log_info "Membuat template konfigurasi di $CONFIG_DIR/guardian.env..."
    cp "$INSTALL_DIR/.env.example" "$CONFIG_DIR/guardian.env"
    sed -i 's|DATABASE_PATH=./guardian.db|DATABASE_PATH=/var/lib/serverinka/guardian.db|g' "$CONFIG_DIR/guardian.env"
    sed -i 's|BACKUP_PATH=./backups|BACKUP_PATH=/var/lib/serverinka/backups|g' "$CONFIG_DIR/guardian.env"
    chmod 600 "$CONFIG_DIR/guardian.env"
    chown serverinka:serverinka "$CONFIG_DIR/guardian.env"
    log_warn "PASTIKAN Anda mengedit $CONFIG_DIR/guardian.env sebelum menjalankan service!"
fi

# 8. Buat Systemd Service Unit
SYSTEMD_SERVICE="/etc/systemd/system/serverinka-guardian.service"
log_info "Membuat systemd service di $SYSTEMD_SERVICE..."

cat <<'EOF' > "$SYSTEMD_SERVICE"
[Unit]
Description=Serverinka Guardian Telegram VPS Control Bot
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=serverinka
Group=serverinka
WorkingDirectory=/opt/serverinka-guardian
EnvironmentFile=/etc/serverinka/guardian.env
Environment=HOME=/home/serverinka
Environment=PATH=/opt/serverinka-guardian/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/serverinka-guardian/.venv/bin/python -m guardian
Restart=always
RestartSec=10s
StandardOutput=journal
StandardError=journal
LimitNOFILE=65536

# Security hardening
ProtectSystem=full
ProtectHome=false
NoNewPrivileges=false

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable serverinka-guardian.service

log_info "====================================================="
log_info "Instalasi Serverinka Guardian Selesai!"
log_info "Langkah selanjutnya:"
log_info "1. Edit konfigurasi: sudo nano $CONFIG_DIR/guardian.env"
log_info "2. Jalankan bot:     sudo systemctl start serverinka-guardian"
log_info "3. Cek status:       sudo systemctl status serverinka-guardian"
log_info "4. Cek log:          sudo journalctl -u serverinka-guardian -f"
log_info "====================================================="
