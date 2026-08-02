#!/usr/bin/env bash
# =====================================================================
# SERVERINKA GUARDIAN — SCRIPT BACKUP DATABASE
# =====================================================================
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
DB_PATH="${2:-./guardian.db}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/guardian_backup_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "[ERROR] Database file $DB_PATH tidak ditemukan!"
    exit 1
fi

echo "[INFO] Membuat backup SQLite database $DB_PATH -> $BACKUP_FILE..."

# Menggunakan sqlite3 command jika tersedia, atau cp jika tidak ada
if command -v sqlite3 &> /dev/null; then
    sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
else
    cp "$DB_PATH" "$BACKUP_FILE"
fi

# Gzip hasil backup
gzip "$BACKUP_FILE"
echo "[INFO] Backup selesai: ${BACKUP_FILE}.gz"

# Hapus backup lama melebihi 7 hari
find "$BACKUP_DIR" -type f -name "guardian_backup_*.db.gz" -mtime +7 -delete
echo "[INFO] Cleanup backup lama (> 7 hari) selesai."
