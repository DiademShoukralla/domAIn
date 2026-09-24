#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

usage() {
  echo "Usage: IMAGE_TAG=<tag> $0 [--compose-file <path>] [--env-file <path>]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file)
      COMPOSE_FILE="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${IMAGE_TAG:-}" ]]; then
  echo "ERROR: IMAGE_TAG is not set" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERROR: Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: Env file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${INGRESS_SITES_DIR:-}" ]]; then
  echo "ERROR: INGRESS_SITES_DIR is not set in $ENV_FILE" >&2
  exit 1
fi

if [[ -z "${INGRESS_CADDY_CONTAINER:-}" ]]; then
  echo "ERROR: INGRESS_CADDY_CONTAINER is not set in $ENV_FILE" >&2
  exit 1
fi

COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE")

wait_for_healthy() {
  local container="$1"
  local attempts="${2:-30}"
  local status="starting"

  for _ in $(seq 1 "$attempts"); do
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || echo "starting")"
    if [[ "$status" == "healthy" ]]; then
      return 0
    fi
    sleep 2
  done

  echo "ERROR: $container did not become healthy (last status: $status)" >&2
  return 1
}

echo "==> Pulling images..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" pull

echo "==> Starting database..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" up -d domain-db
wait_for_healthy domain-db

echo "==> Running migrations..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" run --rm --no-deps domain-api alembic upgrade head

echo "==> Starting services..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" up -d
wait_for_healthy domain-api
wait_for_healthy domain-landing

echo "==> Publishing Caddy site..."
install -m 0644 deploy/caddy-sites/domain.caddy "$INGRESS_SITES_DIR/domain.caddy"
docker exec "$INGRESS_CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile

echo "==> Pruning old images..."
docker image prune -a -f --filter until=1h

echo "Deploy complete."
