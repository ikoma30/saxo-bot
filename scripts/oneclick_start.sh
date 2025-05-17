#!/usr/bin/env bash
set -euo pipefail

ENV=${1:-live}   # live | sim
cd /opt/saxo-bot

# 1. 取得した最新リリースタグを変数に
TAG=$(curl -s https://api.github.com/repos/ikoma30/saxo-bot/releases/latest \
        | jq -r '.tag_name')
export TAG

# 2. 適切な compose ファイルを選択
COMPOSE_FILE="docker/docker-compose.${ENV}.yml"

# 3. イメージ取得＆起動
docker compose -f "${COMPOSE_FILE}" pull
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

# 4. 30 秒以内に healthz==OK を確認
timeout 30 bash -c '
  until curl -sf http://localhost:8080/healthz; do sleep 2; done
'

echo "✅ One-click start (${ENV}) done."
