# M7 — TCP/IP approfondi

Vague 2. Prérequis : M1 (OSI), M6 (routage).

## Objectifs
- Comprendre le contrôle de flux (fenêtre), de congestion (slow-start, cwnd) et les
  retransmissions.
- Mesurer l'impact de la latence, de la perte et de la gigue sur un flux réel.
- Maîtriser `tc netem`, `iperf3`, `ss -ti`, `tshark`.

## Théorie
### 1. Fenêtrage
TCP annonce une fenêtre de réception (rwnd) ; l'émetteur limite ses octets en vol.
La congestion est pilotée côté émetteur (cwnd) : slow-start (×2), congestion avoidance
(+) — un segment perdu divise cwnd. RTT × cwnd détermine le débit utile (loi de
Bit Piped / BDP).

### 2. Retransmissions
Perte → triple ACK → fast retransmit, ou RTO (exponentiel). Avec 2 % de perte aléatoire,
le débit iperf3 s'effondre bien plus que ne le laisse croire le taux brut : chaque
perte ramène cwnd.

### 3. Path MTU
La taille de chemin minimale impose le plafond de segment ; une erreur ICMP
"frag needed" mal filtrée casse les connexions (PMTUD blackhole).

## Labo
`lab/scenario.md` — h1 ↔ r1 ↔ r2 ↔ h2.
But : établir un flux iperf3 de base, imposer `delay 50ms loss 2%` sur le lien WAN
(eth de r1 vers r2), vérifier RTT et débit dégradés, observer cwnd avec `ss -ti`.

## Critères de validation
- Quiz ≥ 70 %.
- TP vérifié par script : qdisc netem présent avec les bons paramètres, RTT ≥ 45 ms
  mesuré par ping, serveur iperf3 actif, connectivité de base.
