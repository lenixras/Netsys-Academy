#!/usr/bin/env bash
# Démarre le launcher netsys-academy en arrière-plan (idempotent).
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8090}"

if curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  echo "déjà en ligne : http://localhost:$PORT"
  exit 0
fi

mkdir -p var
CLAB_CMD="${CLAB_CMD:-$PWD/bin/clab-root}" \
  nohup uv run uvicorn launcher.app:app --host 0.0.0.0 --port "$PORT" >> var/launcher.log 2>&1 &
echo $! > var/launcher.pid

for _ in $(seq 20); do
  curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1 && {
    echo "netsys-academy en ligne : http://localhost:$PORT (pid $(cat var/launcher.pid))"; exit 0; }
  sleep 1
done
echo "échec du démarrage — voir var/launcher.log" >&2
exit 1
