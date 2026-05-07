#!/bin/bash
# ==============================================================================
# KORA Database Backup Script
# ==============================================================================
# Creates a timestamped backup of the PostgreSQL database
# and optionally uploads to S3 for offsite storage.
#
# Usage:
#   ./backup.sh              # Local backup only
#   ./backup.sh --s3         # Backup and upload to S3
#
# Environment variables:
#   POSTGRES_USER      - Database user (default: kora)
#   POSTGRES_DB        - Database name (default: kora)
#   BACKUP_DIR         - Local backup directory (default: /opt/kora/backups)
#   AWS_S3_BUCKET      - S3 bucket for offsite backups
#   BACKUP_RETENTION   - Days to keep local backups (default: 7)
# ==============================================================================

set -euo pipefail

# Configuration
POSTGRES_USER="${POSTGRES_USER:-kora}"
POSTGRES_DB="${POSTGRES_DB:-kora}"
BACKUP_DIR="${BACKUP_DIR:-/opt/kora/backups}"
BACKUP_RETENTION="${BACKUP_RETENTION:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="kora_backup_${TIMESTAMP}.sql.gz"

# Colors for output
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

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Check if we're running in Docker or on host
if command -v docker &> /dev/null && docker ps | grep -q kora-db; then
    log_info "Running backup via Docker..."
    docker exec kora-db pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"
else
    log_info "Running backup via local pg_dump..."
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"
fi

BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
log_info "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Upload to S3 if requested
if [[ "${1:-}" == "--s3" ]]; then
    if [[ -z "${AWS_S3_BUCKET:-}" ]]; then
        log_error "AWS_S3_BUCKET not set. Skipping S3 upload."
    else
        log_info "Uploading to S3: s3://${AWS_S3_BUCKET}/backups/"
        aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${AWS_S3_BUCKET}/backups/${BACKUP_FILE}"
        log_info "S3 upload complete"
    fi
fi

# Clean up old backups
log_info "Cleaning up backups older than ${BACKUP_RETENTION} days..."
find "${BACKUP_DIR}" -name "kora_backup_*.sql.gz" -mtime "+${BACKUP_RETENTION}" -delete 2>/dev/null || true

# List current backups
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "kora_backup_*.sql.gz" | wc -l)
log_info "Current backup count: ${BACKUP_COUNT}"

log_info "Backup completed successfully!"
