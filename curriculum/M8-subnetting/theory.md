# M8 — Adresse IP & sous-réseaux

Vague 2. Prérequis : M1 (OSI).

## Objectifs
- Découper un préfixe en sous-réseaux de taille fixe et en VLSM.
- Retrouver adresse réseau, masque, broadcast et plage d'hôtes instantanément.
- Notation CIDR IPv6 et préfixes /64 par LAN.

## Théorie
### 1. CIDR et masque
`10.0.0.0/24` = préfixe 24 bits → 2^(32-24) adresses, dont réseau et broadcast
non attribuables : 254 hôtes. Le masque = bits réseau à 1.

### 2. Subnetting fixe
n bits d'emprunt → 2^n sous-réseaux de taille divisée par 2^n.
Taille de bloc = 256 - (valeur de l'octet frontière). Ex. /26 → blocs de 64 :
`.0 .64 .128 .192`.

### 3. VLSM
Allouer des sous-réseaux de tailles différentes aux réseaux selon leurs besoins
(d'abord les plus gros), pour gaspiller le minimum d'adresses.

### 4. IPv6
Pas de broadcast ; préfixe /64 par LAN (les 64 bits d'interfaceID), allocation
typique /48 par site. SLAAC dérive l'adresse du MAC (EUI-64) ou d'un ID aléatoire.

## Labo (drills, sans conteneur)
`lab/problems.yaml` — 12 exercices tirés selon l'utilisateur : réseau/masque,
broadcast, nb d'hôtes, choix de préfixe VLSM, notation IPv6.
Répondre dans le terminal web (`python3 -c "import ipaddress; …"`, `ipcalc`) puis
**Vérifier** : correction machine par `check.py` (stdlib `ipaddress`).

## Critères de validation
- Quiz ≥ 70 %.
- TP : 100 % des drills corrects (correction déterministe, sans Moodle requis).
