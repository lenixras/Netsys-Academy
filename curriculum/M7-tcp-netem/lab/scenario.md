# Labo M7 — TCP sous impairment (latence + perte) avec netem et iperf3

**Objectif** : mesurer l'effet réel de la latence et de la perte sur un flux TCP.

## Adressage

| Nœud | Interface | Adresse |
|---|---|---|
| h1 | eth1 | 10.10.10.10/24 (gw 10.10.10.1) |
| r1 | eth1 / eth2 | 10.10.10.1/24 / 10.99.0.1/30 |
| r2 | eth1 / eth2 | 10.99.0.2/30 / 10.10.20.1/24 (gw par défaut r1) |
| h2 | eth1 | 10.10.20.10/24 (gw 10.10.20.1) |

## Étape 1 — Connectivité de base
Configurez les IP ci-dessus, activez `net.ipv4.ip_forward=1` sur r1/r2, routes
statiques (r1: `ip route 10.10.20.0/24 via 10.99.0.2` ; r2 : idem vers 10.10.10.0/24).
`ping -c2 10.10.20.10` depuis h1 doit répondre avec un RTT < 5 ms.

## Étape 2 — Débit de référence
```bash
# h2 :
iperf3 -s -D
# h1 :
iperf3 -c 10.10.20.10 -t 5
```
Notez le débit (Gbit/s attendus).

## Étape 3 — Impairment sur le WAN (r1, interface eth2)
```bash
tc qdisc add dev eth2 root netem delay 50ms loss 2%
```
Re-mesurez : le RTT du ping passe ≈ 50 ms, le débit iperf3 chute brutalement.

## Étape 4 — Observation
```bash
ping -c5 10.10.20.10                                  # rtt >= 50 ms, pertes ICMP
iperf3 -c 10.10.20.10 -t 10 | tail -5                 # débit effondré (retransmissions)
ss -tin dst 10.10.20.10      # depuis un autre onglet si besoin : cwnd, retrans
```
Pour retirer netem : `tc qdisc del dev eth2 root`.

**Vérifier** quand ping ≥ 45 ms mesuré et iperf3 server actif.
