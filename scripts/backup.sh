#!/usr/bin/env bash
# Backs up the Postgres database and VMImages/ (master images + metadata,
# not overlays — overlays are ephemeral by design and excluded).
# Run via cron, e.g.: 0 3 * * * /srv/knpodly/scripts/backup.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/srv/knpodly/backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "==> Backing up Postgres database"
docker compose -f /srv/knpodly/docker-compose.prod.yml exec -T db \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_DIR}/db-${TIMESTAMP}.sql.gz"

echo "==> Backing up VMImages (master images + metadata)"
tar --exclude='*.qcow2.tmp' -czf "${BACKUP_DIR}/vmimages-${TIMESTAMP}.tar.gz" -C /srv/knpodly VMImages VMIcons

echo "==> Pruning backups older than 14 days"
find "$BACKUP_DIR" -name '*.gz' -mtime +14 -delete

echo "Backup complete: ${BACKUP_DIR}"
