#!/bin/bash
# ==============================================================================
# KORA Database Restore Script
# ==============================================================================
# Restores a PostgreSQL database from a backup file.
#
# Usage:
#   ./restore.sh <backup_file>
#   ./restore.sh kora_backup_20260221_120000.sql.gz
#   ./restore.sh --latest                              # Restore most recent backup
#   ./restore.sh --from-s3 kora_backup_xyz.sql.gz     # Download and restore from S3
#
# WARNING: This will DROP the existing database and recreate it!
# ==============================================================================

set -euo pipefail

# Configuration
POSTGRES_USER="${POSTGRES_USER:-kora}"
POSTGRES_DB="${POSTGRES_DB:-kora}"
BACKUP_DIR="${BACKUP_DIR:-/opt/kora/backups}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <backup_file> | --latest | --from-s3 <file>"
    echo ""
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}"/kora_backup_*.sql.gz 2>/dev/null || echo "  (none found)"
    exit 1
fi

BACKUP_FILE=""

if [[ "$1" == "--latest" ]]; then
    BACKUP_FILE=$(ls -t "${BACKUP_DIR}"/kora_backup_*.sql.gz 2>/dev/null | head -n1)
    if [[ -z "${BACKUP_FILE}" ]]; then
        log_error "No backup files found in ${BACKUP_DIR}"
        exit 1
    fi
    log_info "Using latest backup: ${BACKUP_FILE}"

elif [[ "$1" == "--from-s3" ]]; then
    if [[ -z "${2:-}" ]]; then
        log_error "Please specify the S3 backup file name"
        exit 1
    fi
    if [[ -z "${AWS_S3_BUCKET:-}" ]]; then
        log_error "AWS_S3_BUCKET not set"
        exit 1
    fi
    S3_FILE="$2"
    BACKUP_FILE="${BACKUP_DIR}/${S3_FILE}"
    log_info "Downloading from S3: s3://${AWS_S3_BUCKET}/backups/${S3_FILE}"
    aws s3 cp "s3://${AWS_S3_BUCKET}/backups/${S3_FILE}" "${BACKUP_FILE}"

else
    if [[ -f "$1" ]]; then
        BACKUP_FILE="$1"
    elif [[ -f "${BACKUP_DIR}/$1" ]]; then
        BACKUP_FILE="${BACKUP_DIR}/$1"
    else
        log_error "Backup file not found: $1"
        exit 1
    fi
fi

log_warn "====================================="
log_warn "WARNING: This will DROP and RECREATE"
log_warn "the database '${POSTGRES_DB}'!"
log_warn "====================================="
echo ""
read -p "Type 'yes' to continue: " CONFIRM

if [[ "${CONFIRM}" != "yes" ]]; then
    log_info "Restore cancelled"
    exit 0
fi

log_info "Restoring from: ${BACKUP_FILE}"

# Check if running in Docker
if command -v docker &> /dev/null && docker ps | grep -q kora-db; then
    log_info "Restoring via Docker..."

    # Drop and recreate database
    docker exec kora-db psql -U "${POSTGRES_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    docker exec kora-db psql -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE ${POSTGRES_DB};"

    # Restore
    gunzip -c "${BACKUP_FILE}" | docker exec -i kora-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
else
    log_info "Restoring via local psql..."

    # Drop and recreate database
    psql -U "${POSTGRES_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    psql -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE ${POSTGRES_DB};"

    # Restore
    gunzip -c "${BACKUP_FILE}" | psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
fi

log_info "Database restored successfully!"
log_info "You may need to restart the API service: docker compose restart api"
