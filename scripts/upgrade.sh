#!/usr/bin/env bash
# Zero/low-downtime-ish upgrade: pull latest code, rebuild images, run
# Alembic migrations, then recreate containers.
set -euo pipefail
cd /srv/knpodly

echo "==> Pulling latest changes"
git pull

echo "==> Building updated images"
docker compose -f docker-compose.prod.yml build

echo "==> Running database migrations"
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

echo "==> Recreating containers"
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "==> Done. Tail logs with: docker compose -f docker-compose.prod.yml logs -f"
