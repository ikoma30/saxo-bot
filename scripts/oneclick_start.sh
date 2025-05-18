#!/usr/bin/env bash

set -euo pipefail

ENV=${1:-}
if [[ "$ENV" != "live" && "$ENV" != "sim" ]]; then
  echo "Usage: $0 {live|sim}"
  exit 1
fi

ENV_FILE="/opt/saxo-bot/.env.${ENV}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: Environment file $ENV_FILE not found"
  exit 1
fi

source "${ENV_FILE}"

TAG=$(curl -s https://api.github.com/repos/ikoma30/saxo-bot/releases/latest | jq -r '.tag_name')
export TAG  # Register in environment variable to allow docker-compose to expand ${TAG}

COMPOSE_FILE="/opt/saxo-bot/docker-compose.${ENV}.yml"
docker compose -f "${COMPOSE_FILE}" pull
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

for i in {1..30}; do
  if curl -fs http://localhost:8080/healthz; then
    echo "✅ oneclick_start ${ENV} completed."
    exit 0
  fi
  sleep 1
done

echo "❌ Healthz check failed after 30 seconds"
exit 1
