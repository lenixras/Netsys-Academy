# Labo M4 — Services critiques : DNS, DHCP, NTP, SSH

**Objectif** : sur `srv`, faire tourner les quatre services essentiels d'un réseau
(name-server, DHCP, NTP, SSH) et les faire consommer depuis `client1`. Il n'y a
pas de systemd dans les conteneurs : ** chaque service se lance à la main **.

## Plan d'adressage (à respecter)

| Nœud | Interface | Adresse | Rôle |
|---|---|---|---|
| srv | eth1 | 10.1.40.1/24 | DNS + DHCP + NTP + SSH (`ns.lab4.local`) |
| gw | eth1 / eth2 / eth3 | 10.1.40.254 / 10.1.41.254 / 10.1.42.254 | passerelle, forwarding |
| client1 | eth1 | 10.1.41.10/24 | station de test (`web.lab4.local`) |
| client2 | eth1 | 10.1.42.10/24 | second LAN (optionnel) |

Câblage : `srv:eth1↔gw:eth1`, `client1:eth1↔gw:eth2`, `client2:eth1↔gw:eth3`.
Le DHCP de `srv` desservira son propre sous-réseau (10.1.40.100-150) — pas de
client DHCP réel dans l'image, on valide la **configuration** et l'écoute du port 67.

Modèles de fichiers déjà livrés par le launcher : `/root/named.conf.template`,
`/root/db.lab4.local.template`, `/root/dnsmasq.conf.template`,
`/root/chrony-server.conf.template` (srv) et `/root/chrony-client.conf.template`
(client1). Les zones `A_REMPLACER`, `RESEAU,DERNIERERESEAU`, `PASSERELLE` sont à
compléter avec l'éditeur de fichiers intégré (onglet Fichier) ou par `sed`.

## Étape 0 — Base réseau (sur chaque nœud)

```bash
# gw :
ip link set eth1 up; ip link set eth2 up; ip link set eth3 up
ip addr add 10.1.40.254/24 dev eth1; ip addr add 10.1.41.254/24 dev eth2; ip addr add 10.1.42.254/24 dev eth3
sysctl -w net.ipv4.ip_forward=1
# srv :
ip link set eth1 up; ip addr add 10.1.40.1/24 dev eth1; ip route replace default via 10.1.40.254
# client1 :
ip link set eth1 up; ip addr add 10.1.41.10/24 dev eth1; ip route replace default via 10.1.41.254
```
Test : `ping -c2 10.1.40.1` depuis client1.

## Étape 1 — DNS (named / bind9)

Copie les modèles puis complète le A de `web.lab4.local` avec l'IP de client1 :
```bash
cp /root/named.conf.template /root/named.conf
cp /root/db.lab4.local.template /root/db.lab4.local
sed -i 's|A_REMPLACER|10.1.41.10|' /root/db.lab4.local
named-checkconf /root/named.conf && named-checkzone lab4.local /root/db.lab4.local
named -c /root/named.conf -g > /root/named.log 2>&1 &
```
Test depuis client1 : `dig @10.1.40.1 web.lab4.local +short` → `10.1.41.10`.

## Étape 2 — DHCP (dnsmasq)

`dnsmasq` joue ici le rôle de serveur DHCP **uniquement** (`port=0` : le 53 est
déjà pris par named — deux services ne peuvent pas écouter le même port).
Complète le modèle (pool sur le réseau de `srv`, passerelle = gw) :
```bash
cp /root/dnsmasq.conf.template /root/dnsmasq.conf
sed -i -e 's|RESEAU,DERNIERERESEAU|10.1.40.100,10.1.40.150,255.255.255.0,8h|' -e 's|PASSERELLE|10.1.40.254|' /root/dnsmasq.conf
dnsmasq --test --conf-file=/root/dnsmasq.conf   # « syntax check OK » exigé
dnsmasq --conf-file=/root/dnsmasq.conf          # se lance en tâche de fond
```
Test : `ss -uln | grep :67` montre une écoute UDP sur 0.0.0.0:67.

## Étape 3 — NTP (chrony)

Sur `srv` (source de référence locale : `local stratum 10`), puis sur `client1` :
```bash
# srv :
mkdir -p /var/lib/chrony
cp /root/chrony-server.conf.template /root/chrony.conf
chronyd -f /root/chrony.conf
# client1 :
mkdir -p /var/lib/chrony
cp /root/chrony-client.conf.template /root/chrony.conf
chronyd -f /root/chrony.conf
sleep 5; chronyc -a makestep; chronyc -n sources
```
`chronyc -n sources` doit montrer `^*` ou `^+` sur `10.1.40.1` (attend quelques
secondes que le sondage ~4 s ait lieu).

## Étape 4 — SSH par clé

`srv` a déjà un compte `svc` (sans mot de passe) et ses clés d'hôte. Sur `srv` :
```bash
mkdir -p /run/sshd && /usr/sbin/sshd
```
Sur `client1`, génère une paire sans passphrase, puis **publie la clé publique** :
```bash
mkdir -p /root/.ssh && ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519
cat /root/.ssh/id_ed25519.pub
```
Copie cette ligne, ouvre l'éditeur de fichiers intégré sur le nœud `srv`,
colle-la dans `/home/svc/.ssh/authorized_keys` (une clé par ligne), puis :
```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=no svc@10.1.40.1 hostname
```
Avec `BatchMode=yes` la connexion **échoue sans clé autorisée** : le mot de passe
n'est pas une option — c'est précisément l'authenticité de la tâche.

## Étape 5 — Vérification

Les 6 checks valident : named actif, résolution `web.lab4.local`, config dnsmasq
valide, écoute DHCP 67, source NTP `10.1.40.1` en ligne côté client1, connexion
SSH clé vers `svc@10.1.40.1`. Clique **Vérifier** pour pousser la note (10 pts).
