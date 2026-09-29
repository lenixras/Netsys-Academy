# Labo M17 — Capstone : petite infrastructure d'entreprise

Aucun systemd, aucune automation : **tout à la main**, nœud par nœud, dans les
terminaux web. Le labo est noté sur **15 points** (8 checks). Temps conseillé : 60 min.

## Cahier des charges

Une PME déploie son réseau :

1. Un switch d'accès `acc1` fait passer le poste `pc1` dans le **VLAN 100**
   (bridge linux, `vlan_filtering 1`, port d'accès non taggé côté pc1 ; le port
   vers `core1` transporte le VLAN 100 en **non taggé** — c'est une interface
   d'accès côté cœur).
2. `core1` est la passerelle du VLAN 100 (`10.17.100.1`) et route vers le reste.
3. Routage statique `core1 ↔ core2 ↔ srv1` (préfixes d'interco ci-dessous).
4. `srv1` rend le DNS interne via **dnsmasq** (port 53) : le nom
   `intranet.capstone` doit résoudre vers l'IP de `srv1`.
5. `core1` fait le **NAT (masquerade)** côté `ext` : `pc1` doit joindre
   `20.20.20.10` (l'Internet simulé).
6. **Isolation** : depuis `ext`, on ne doit PAS pouvoir joindre `pc1`
   (filtre de forwarding sur `core1`, politique « entrant interdit »).

## Plan d'adressage (imposé)

| Nœud | Interface | Addressage | Rôle |
|------|-----------|------------|------|
| pc1 | eth1 | 10.17.100.10/24, GW 10.17.100.1 | poste VLAN 100 |
| acc1 | eth1 / eth2 | (bridge br0) | accès VLAN 100 |
| core1 | eth1 | 10.17.100.1/24 | passerelle VLAN 100 |
| core1 | eth2 | 10.17.0.1/30 | interco core1↔core2 |
| core2 | eth1 | 10.17.0.2/30 | idem |
| core2 | eth2 | 10.17.200.1/24 | passerelle VLAN serveurs |
| srv1 | eth1 | 10.17.200.50/24, GW 10.17.200.1 | DNS intranet.capstone |
| core1 | eth3 | 20.20.20.1/24 | sortie WAN (NAT) |
| ext | eth1 | 20.20.20.10/24, GW 20.20.20.1 | Internet simulé |

Routes statiques minimales : `core1` → `10.17.200.0/24 via 10.17.0.2` ;
`core2` → `10.17.100.0/24 via 10.17.0.1` ; par défaut chez `srv1` et `ext` ;
forwarding IPv4 activé sur `core1` et `core2`.

## Ordre de travail conseillé

1. `ip link`/`ip addr` sur tous les nœuds (montez aussi les liens).
2. Pont VLAN sur `acc1` :
   `ip link add name br0 type bridge vlan_filtering 1` puis `bridge vlan add dev eth1 vid 100 pvid untagged`.
3. Routage + `sysctl -w net.ipv4.ip_forward=1` sur les cœurs.
4. NAT + filtre sur `core1` (nftables, iptables n'est pas installé) :
   ```
   nft add table ip nat
   nft 'add chain ip nat po { type nat hook postrouting priority srcnat; }'
   nft add rule ip nat po oifname eth3 masquerade
   nft add table ip filter
   nft 'add chain ip filter fw { type filter hook forward priority 0; policy accept; }'
   nft add rule ip filter fw iifname eth3 ct state established,related accept
   nft add rule ip filter fw iifname eth3 ip daddr 10.17.100.0/24 counter drop
   ```
5. DNS sur `srv1` :
   `dnsmasq --port=53 --user=root --group=root --no-resolv --address=/intranet.capstone/10.17.200.50`
6. Tests vous-mêmes avant **Vérifier** : `ping`, `dig intranet.capstone @10.17.200.50`,
   `bridge vlan show`, `ip route`.

## Barème (15 pts)

ping pc1→GW (2) · ping pc1→srv1 (2) · ping pc1→ext via NAT (2) · dig intranet (3) ·
VLAN 100 sur port acc1 (2) · route users sur core2 (1) · dnsmasq actif (1) ·
ext ne joindra pas pc1 (2).
