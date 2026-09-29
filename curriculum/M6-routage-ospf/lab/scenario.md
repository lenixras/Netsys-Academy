# Labo M6 — OSPF sur FRRouting (triangle de routeurs)

**Objectif** : établir OSPF entre `r1`, `r2`, `r3` (area 0), annoncer tous les
préfixes, et faire se répondre `h1 ↔ h2` via le routage dynamique.

Les routeurs tournent sous **FRR 10** : chez lui, OSPF s'active **par interface**
(`ip ospf area 0`), il n'y a plus de déclaration `network … area`.

## Plan d'adressage (à respecter)

| Lien | Sous-réseau | r1 | r2 | r3 |
|---|---|---|---|---|
| r1–r2 (eth1–eth1) | 10.0.12.0/29 | .1 | .2 | — |
| r2–r3 (eth2–eth1) | 10.0.23.0/29 | — | .2 | .3 |
| r1–r3 (eth2–eth2) | 10.0.13.0/29 | .1 | — | .3 |
| LAN h1 (r1:eth3) | 10.10.10.0/24 | .1 | | h1=.10 |
| LAN h2 (r3:eth3) | 10.10.20.0/24 | .1 (r3) | | h2=.10 |
| Loopbacks | 2.2.2.2/32 (r1), 3.3.3.3/32 (r2), 4.4.4.4/32 (r3) |

## Étape 1 — Hôtes
```bash
# h1 :
ip addr add 10.10.10.10/24 dev eth1 && ip link set eth1 up && ip route replace default via 10.10.10.1
# h2 :
ip addr add 10.10.20.10/24 dev eth1 && ip link set eth1 up && ip route replace default via 10.10.20.1
```

## Étape 2 — OSPF sur r1
```
r1# vtysh
r1# conf t
r1(config)# interface eth1
r1(config-if)# ip address 10.0.12.1/29
r1(config-if)# ip ospf network point-to-point
r1(config-if)# ip ospf area 0
r1(config-if)# exit
r1(config)# interface eth2
r1(config-if)# ip address 10.0.13.1/29
r1(config-if)# ip ospf network point-to-point
r1(config-if)# ip ospf area 0
r1(config-if)# exit
r1(config)# interface eth3
r1(config-if)# ip address 10.10.10.1/24
r1(config-if)# ip ospf area 0
r1(config-if)# exit
r1(config)# interface lo
r1(config-if)# ip address 2.2.2.2/32
r1(config-if)# ip ospf area 0
r1(config-if)# exit
r1(config)# router ospf
r1(config-router)# ospf router-id 2.2.2.2
r1(config-router)# end
```

`ip ospf network point-to-point` sur les liens routiers : sinon le lien est traité
en broadcast et une élection DR retarde (bloque) l'adjacence Full.

## Étape 3 — r2 et r3
Même patron : interfaces du plan d'adressage + `ip ospf area 0` partout,
`point-to-point` sur les liens entre routeurs, `ospf router-id` (3.3.3.3, 4.4.4.4).

## Étape 4 — Vérifications
```bash
vtysh -c "show ip ospf neighbor"   # 2 voisins Full sur r1 et r3
vtysh -c "show ip route ospf"      # 10.10.20.0/24, 4.4.4.4/32 chez r1
ping -c2 10.10.20.10               # depuis h1
```

Puis **Vérifier** pour la note.
