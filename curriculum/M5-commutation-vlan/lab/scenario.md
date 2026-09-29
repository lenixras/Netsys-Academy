# Labo M5 — Commutation, VLANs, STP et routage inter-VLAN

**Objectif** : rendre `h1 (VLAN 10) ↔ h3 (VLAN 10)` communicants via un trunk entre
`sw1` et `sw2`, couper la boucle avec STP, et routage `h1 ↔ h2 (VLAN 20)` via le
routeur `r1` en router-on-a-stick.

## Plan d'adressage (à respecter)

| Nœud | Interface | Adresse | Passerelle |
|---|---|---|---|
| h1 | eth1 | 10.10.0.2/24 | 10.10.0.1 |
| h3 | eth1 | 10.10.0.3/24 | 10.10.0.1 |
| h2 | eth1 | 10.20.0.2/24 | 10.20.0.1 |
| r1 | eth1.10 | 10.10.0.1/24 | — |
| r1 | eth1.20 | 10.20.0.1/24 | — |

Câblage (déjà fait) : `h1↔sw1:eth3`, `h2↔sw2:eth3`, `h3↔sw2:eth4`,
`r1↔sw1:eth4` (trunk), `sw1:eth1↔sw2:eth1` et `sw1:eth2↔sw2:eth2` (boucle).

## Étape 1 — Hôtes
Sur chaque hôte :
```bash
ip addr add 10.10.0.2/24 dev eth1 && ip link set eth1 up      # h1 (adapter par hôte)
ip route replace default via 10.10.0.1    # remplace la route de management docker
```

## Étape 2 — Ponts et VLANs sur les switches
Sur `sw1` et `sw2` :
```bash
ip link set eth1 up; ip link set eth2 up; ip link set eth3 up; ip link set eth4 up
ip link add name br0 type bridge
ip link set eth1 master br0; ip link set eth2 master br0; ip link set eth3 master br0; ip link set eth4 master br0
ip link set br0 up
ip link set dev br0 type bridge vlan_filtering 1
```
- **sw1** : `eth3` access VLAN 10, `eth1`/`eth2`/`eth4` trunk 10+20 taggés, `eth4` vers r1 :
```bash
bridge vlan add dev eth3 vid 10 pvid untagged && bridge vlan del dev eth3 vid 1
for p in eth1 eth2 eth4; do bridge vlan add dev $p vid 10 && bridge vlan add dev $p vid 20; done
```
- **sw2** : `eth3` access VLAN 20, `eth4` access VLAN 10, `eth1`/`eth2` trunk 10+20 :
```bash
bridge vlan add dev eth3 vid 20 pvid untagged && bridge vlan del dev eth3 vid 1
bridge vlan add dev eth4 vid 10 pvid untagged && bridge vlan del dev eth4 vid 1
for p in eth1 eth2; do bridge vlan add dev $p vid 10 && bridge vlan add dev $p vid 20; done
```
Vérifie : `bridge vlan show`.

## Étape 3 — Spanning-tree
`sw1` est la racine (priorité 4096), STP activé partout :
```bash
# sw1 :
ip link set dev br0 type bridge stp_state 1 priority 4096
# sw2 :
ip link set dev br0 type bridge stp_state 1
```
Après convergence (≈30 s), un port de `sw2` (eth1 ou eth2) doit passer en
`state discarding` : `watch -n5 bridge link show`.

## Étape 4 — Routage inter-VLAN (r1)
```bash
ip link set eth1 up
ip link add link eth1 name eth1.10 type vlan id 10
ip link add link eth1 name eth1.20 type vlan id 20
ip addr add 10.10.0.1/24 dev eth1.10; ip addr add 10.20.0.1/24 dev eth1.20
ip link set eth1.10 up; ip link set eth1.20 up
sysctl -w net.ipv4.ip_forward=1
```

## Étape 5 — Tests
```bash
ping -c2 10.10.0.3      # h1 → h3 (même VLAN via trunk)
ping -c2 10.20.0.2      # h1 → h2 (routé via r1)
```

Quand tout répond, clique **Vérifier** pour pousser la note.
