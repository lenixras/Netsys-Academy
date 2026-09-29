#!/usr/bin/env bash
# Arrête le launcher (laisse les sessions de lab en vie : le relanceur les ré-adoppte).
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8090}"

[ -f var/launcher.pid ] && kill "$(cat var/launcher.pid)" 2>/dev/null || true
# filet : le processus qui écoute encore sur le port (uv run fourche uvicorn)
P=$(ss -ltnp 2>/dev/null | grep ":$PORT " | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2) || true
[ -n "${P:-}" ] && kill "$P" 2>/dev/null || true
rm -f var/launcher.pid
sleep 1
if curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  echo "arrêt échoué — vérifier var/launcher.log" >&2
  exit 1
fi
echo "launcher arrêté"
