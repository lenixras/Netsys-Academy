#!/usr/bin/env bash
# Installation from scratch de netsys-academy sur un hôte Linux (WSL2 inclus).
# Prérequis : docker fonctionnel + uv. sudo optionnel (modules noyau, best-effort).
set -euo pipefail
cd "$(dirname "$0")"

fail() { echo "ERREUR: $*" >&2; exit 1; }
ok()   { echo "  ✓ $*"; }

echo "== vérification des prérequis =="
command -v docker >/dev/null || fail "docker manquant (installez docker-ce)"
docker info >/dev/null 2>&1 || fail "daemon docker injoignable (dockerd démarré ?)"
command -v uv >/dev/null || fail "uv manquant : curl -LsSf https://astral.sh/uv/install.sh | sh"
ok "docker + uv présents"

echo "== modules noyau requis par les labs (best-effort, sudo -n) =="
for m in bridge 8021q veth br_netfilter ip_tables nftables nf_nat sch_netem; do
  if lsmod | grep -q "^${m} "; then ok "$m déjà chargé"
  elif sudo -n modprobe "$m" 2>/dev/null; then ok "$m chargé"
  else echo "  ! $m non vérifiable (built-in ou sudo requis — ignorez si les labs tournent)"; fi
done

echo "== containerlab (binaire hôte dans ~/.local/bin) =="
if command -v containerlab >/dev/null || [ -x "$HOME/.local/bin/containerlab" ]; then
  ok "containerlab présent"
else
  url=$(curl -fsSL https://api.github.com/repos/srl-labs/containerlab/releases/latest \
        | sed -n 's/.*"browser_download_url": *"\([^"]*Linux_x86_64\.tar\.gz\)".*/\1/p' | head -1)
  [ -n "$url" ] || fail " Impossible de récupérer la dernière release containerlab"
  mkdir -p "$HOME/.local/bin"
  curl -fsSL "$url" | tar xz -C "$HOME/.local/bin" containerlab
  ok "containerlab installé dans ~/.local/bin (ajoutez-le à votre PATH)"
fi

echo "== images des nœuds de lab =="
docker build -q -t netsys/labnode:1 images/labnode >/dev/null && ok "netsys/labnode:1 (outil clab-root)"
docker build -q --build-arg FULL=1 -t netsys/labnode:2 images/labnode >/dev/null && ok "netsys/labnode:2 (nœuds de lab)"
docker build -q --build-arg FULL=2 -t netsys/labnode:3 images/labnode >/dev/null && ok "netsys/labnode:3 (services: ldap/mail/v6/mon)"
docker build -q -t netsys/frrlab:1 images/frrlab >/dev/null && ok "netsys/frrlab:1 (ospfd)"
docker build -q -t netsys/frrlab:2 images/frrlab2 >/dev/null && ok "netsys/frrlab:2 (bgpd)"
docker image inspect frrouting/frr:latest >/dev/null 2>&1 || docker pull -q frrouting/frr:latest
ok "frrouting/frr:latest disponible"

echo "== dépendances python =="
uv sync --quiet && ok "venv synchronisé"

mkdir -p var
echo
echo "Installation terminée. Démarrer : ./start.sh   (puis http://localhost:8090)"
