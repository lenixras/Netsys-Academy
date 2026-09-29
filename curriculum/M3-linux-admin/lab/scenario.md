# Labo M3 — Linux administrateur : users/groups, réseau, sysctl, logs

**Objectif** : exercer les gestes de base de l'administrateur système sur un nœud
isolé : créer un compte avec un UID imposé, gérer l'appartenance à un groupe,
ajouter une adresse IP secondaire avec `ip`, activer le forwarding IPv4 avec `sysctl`,
écouter un port avec `ss` et produire un fichier de journal applicatif.

- Nœud : `admin1` (un seul). Vous êtes **root** dans le terminal web.
- `eth1` est déjà câblée en boucle vers `eth2` sur le nœud même (interface présente et
  utilisable). `eth0` = réseau de management `clab-m3` (10.198.11.0/24).
- Conteneur Debian **sans systemd** : pas de `systemctl`/`journalctl` réels — le cours
  les présente en théorie ; ici on travaille sur `/etc`, `/proc` et `/var/log`.

## Étape 1 — Créer l'utilisateur `devops` avec un UID imposé

Le plan d'adressage des identités exige **UID/GID 1500** pour `devops` :

```bash
useradd -u 1500 -m -s /bin/bash devops
getent passwd devops
tail -1 /etc/passwd
```

`-u 1500` fixe l'UID (le GID du groupe privé homonyme suit, lui aussi 1500), `-m`
crée le home `/home/devops`, `-s` définit le shell. La ligne attendue dans
`/etc/passwd` est :

```
devops:x:1500:1500::/home/devops:/bin/bash
```

**Vérif** : `user_devops_uid` (2 pts) — contenu de `getent passwd devops`.

## Étape 2 — Groupe `staff`, membre `devops`

Le groupe `staff` peut déjà exister (image Debian) ; `-f` rend la commande idempotente.
Ajoutez `devops` comme membre **sans toucher à son groupe principal** (`-a` = append,
sans lui `usermod -G` écrase les groupes secondaires) :

```bash
groupadd -f staff
usermod -aG staff devops
id devops
id -nG devops
getent group staff
```

**Vérif** : `devops_membre_staff` (1 pt) — `staff` doit apparaître dans `id -nG devops`.

## Étape 3 — Adresse IP secondaire sur `eth1`

Observez d'abord l'état réseau, puis ajoutez l'adresse du plan sur `eth1`.
`ip addr add` **ajoute** une adresse sans supprimer les autres (contrairement à
l'ancien `ifconfig ...` qui les remplaçait) :

```bash
ip -br a
ip link set eth1 up
ip addr add 10.198.11.50/24 dev eth1
ip -br a show eth1
ip addr show dev eth1
ip route
```

**Vérif** : `ip_secondaire_eth1` (2 pts) — `ip -br a show eth1` doit contenir
`10.198.11.50/24`.

## Étape 4 — Activer le forwarding IPv4 avec sysctl

Le nœud démarre avec le forwarding **désactivé** : c'est un routeur potentiel, il faut
le dire explicitement. `sysctl -w` applique la valeur immédiatement (non persistant —
ici le nœud est jetable, la persistance se fait via `/etc/sysctl.d/`, voir le cours) :

```bash
cat /proc/sys/net/ipv4/ip_forward     # 0 au départ
sysctl -w net.ipv4.ip_forward=1
cat /proc/sys/net/ipv4/ip_forward     # 1 attendu
```

**Vérif** : `ip_forward_actif` (2 pts) — lecture de `/proc/sys/net/ipv4/ip_forward`.

## Étape 5 — Un service en écoute, vérifié avec `ss`

La sandbox n'embarque pas `nc` (netcat) ; on utilise l'équivalent Python, un serveur
HTTP qui **écoute** en TCP sur le port 8080, lancé en arrière-plan :

```bash
nohup python3 -m http.server 8080 > /dev/null 2>&1 &
ss -tln
ss -tln | grep 8080
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/
```

`ss -tln` : **t** cp, **l** istening, numérique (pas de résolution de noms). Comparez
avec `ss -tan` (toutes connexions TCP) et `ss -a` (tout).

**Vérif** : `port_ecoute_8080` (2 pts) — une ligne `:8080` dans `ss -tln`.

## Étape 6 — Journaliser dans `/var/log/deploy.log`

`logger` existe dans l'image mais écrit vers le démon syslog — **absent** dans le
conteneur. En sandbox, la journalisation fiable se fait par **redirection** (`>>`
ajoute une ligne, `>` écrase) :

```bash
echo "$(date '+%F %T') deploiement app v1 OK" >> /var/log/deploy.log
test -s /var/log/deploy.log && echo "journal non vide"
cat /var/log/deploy.log
ls -l /var/log/
```

**Vérif** : `log_deploy_non_vide` (1 pt) — `test -s /var/log/deploy.log`.

## Étape 7 — Note finale

Cliquez **Vérifier** : 10 points sur 6 checks. Si un check manque, relisez l'étape
correspondante et le cours (`theory.md`) — sections iproute2, sysctl et logs.
