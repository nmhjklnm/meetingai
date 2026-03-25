#!/usr/bin/env bash
# Remote deployment script — runs ON the server
set -e

DEPLOY_DIR="${DEPLOY_DIR:-/home/ubuntu/meetingai}"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$DEPLOY_DIR"

echo "[1/4] Pulling latest code..."
git fetch origin main
git reset --hard origin/main

echo "[2/4] Building images..."
docker compose -f "$COMPOSE_FILE" build --parallel

echo "[3/4] Restarting services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "[4/4] Cleaning up old images..."
docker image prune -f

echo ""
echo "=== Deployment complete ==="
docker compose -f "$COMPOSE_FILE" ps
