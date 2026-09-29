# Runbook hôte WSL2 (cette machine)

## Prérequis racine (une fois)
```bash
sudo modprobe bridge 8021q sch_netem br_netfilter
echo -e "bridge\n8021q\nsch_netem\nbr_netfilter" | sudo tee /etc/modules-load.d/netsys.conf
# containerlab (binaire + service systemd, non requis hors systemd) :
curl -sL https://github.com/srl-labs/containerlab/releases/latest/download/ \
  containerlab_$(uname -m)-Linux.tar.gz | tar xz -C /tmp && sudo install /tmp/containerlab /usr/local/bin/
```
containerlab doit tourner en root (netlink) : lancer le launcher avec sudo, ou
`sudo visudo` → `sfd ALL=(ALL) NOPASSWD: /usr/local/bin/containerlab` puis
`export CLAB_CMD="sudo -n containerlab"` avant de démarrer le launcher.

## Images
```bash
docker build --build-arg FULL=1 -t netsys/labnode:2 images/labnode
docker pull frrouting/frr:latest
```

## Lancer
```bash
cd netsys-academy
uv run uvicorn launcher.app:app --host 0.0.0.0 --port 8090        # + sudo/CLAB_CMD si besoin
# navigateur : http://localhost:8090
```

## Limites connues de cet hôte
- RAM 3,6 Go (~1,8 Go dispo avec n8n/chromadb/floci) → `NETSYS_MAX_SESSIONS=2` par défaut ;
  couper les stacks perso pendant les E2E si needed.
- `mac80211_hwsim` absent du noyau WSL2 standard → lab M9 Wi-Fi non testable ici.
- mstpd : absent de l'image labnode → les labs M5 utilisent le STP du bridge noyau
  (`stp_state 1`), ce qui est pédagogiquement équivalent pour 802.1D.
- sudo non interactionnel : demander à l'utilisateur d'exécuter les commandes racine via `!`.

## Vérifier l'hôte
```bash
containerlab version
ip link add d0 type dummy && tc qdisc add dev d0 root netem delay 10ms && tc qdisc show dev d0 \
  && tc qdisc del dev d0 root && ip link del d0
docker run --rm --entrypoint sh netsys/labnode:1 -c 'iperf3 -v | head -1; bridge -V'
```
