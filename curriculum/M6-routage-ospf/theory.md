# M6 — Routage (statique, OSPF, BGP intro)

Vague 2. Prérequis : M1 (OSI), M5 (commutation), M8 (adressage).

## Objectifs
- Configurer des routes statiques et comprendre la route par défaut.
- Mettre en œuvre OSPFv2 : voisins, area 0, annonce de réseaux, coût métrique.
- Lire les tables de routage et le lien-state database.
- Introduction BGP : AS, eBGP vs iBGP, policy de haut niveau (non évalué en lab).

## Théorie
### 1. Routage statique
`ip route <réseau>/<masque> via <next-hop>` : chemin décidé par l'administrateur.
Simple mais non résilient — chaque lien coupé demande une intervention.

### 2. OSPF (link-state)
Chaque routeur inonde des LSAs (état de ses liens) ; tous construisent la même LSDB
et calculent le plus court chemin (Dijkstra) vers chaque préfixe.
Notions clés : Router ID, Hello/Dead, états de voisinage (Down → Init → 2-Way →
ExStart → Loading → **Full**), area (backbone 0.0.0.0), coût = réfBW/BW,
réseaux annoncés via `network <ip> <wildcard> area 0`.
FRRouting implémente OSPF comme un routeur professionnel (`vtysh`).

### 3. BGP (vector-path) — introduction
Protocole inter-domaines par politiques : AS, eBGP/iBGP, attributs
(NEXTHOP, AS_PATH, LOCAL_PREF, MED). Enseigné en théorie en M6, approfondi en capstone.

## Labo
`lab/scenario.md` — 3 routeurs FRR en triangle + 2 hôtes.
But : sessions OSPF Full, annonce de tous les préfixes, ping h1↔h2 via le plan
d'adressage fourni.

## Critères de validation
- Quiz ≥ 70 %.
- TP vérifié par script : voisins Full ×2 sur r1, préfixes OSPF dans les tables,
  ping inter-hôtes, area correcte.
