# M5 — Commutation & VLANs

Vague 2. Prérequis : M1 (modèle OSI), M3 (Linux administrateur).

## Objectifs
- Construire un bridge 802.1Q sur Linux (vlan_filtering, PVID, ports access/trunk).
- Comprendre le découpage d'un domaine de diffusion par VLAN.
- Mettre en œuvre le spanning-tree (kernel STP) pour casser une boucle physique.
- Réaliser le routage inter-VLAN (router-on-a-stick avec sous-interfaces 802.1Q).

## Théorie
### 1. Commutation
Un switch apprend les adresses MAC source de ses ports et relaie les trames vers le
port de destination (table FDB). Sans VLAN, tous les ports forment un seul domaine de
diffusion : un broadcast (ARP, DHCP) touche toute l'entreprise.

### 2. 802.1Q
La norme ajoute un tag VLAN (12 bits, 4094 VLANs) dans la trame Ethernet.
- **Port access** : un seul VLAN, trames non tagguées côté équipement, PVID ajouté/retiré.
- **Port trunk** : plusieurs VLANs, trames taggées entre équipements.
Sous Linux, `bridge vlan` expose le même modèle : `vid <n> pvid untagged` (access)
vs `vid <n>` seul (trunk taggé).

### 3. Spanning-tree
Deux liens redondants = boucle = tempête de broadcast. STP (802.1D) bloque un port
désigné (état blocking) pour garder un arbre sans boucle, tout en gardant le lien en
secours. Sur Linux : `stp_state 1` sur le bridge.

### 4. Routage inter-VLAN
Les VLANs séparent les sous-réseaux : le trafic inter-VLAN passe par un routeur.
Pattern *router-on-a-stick* : un lien trunk, une sous-interface par VLAN
(`ip link add link eth1 name eth1.10 type vlan id 10`), chaque sous-interface étant la
passerelle du VLAN.

## Labo
`lab/scenario.md` — 6 nœuds : 2 switches Linux (labnode), 1 routeur, 3 hôtes.
But : VLANs 10/20, trunk entre switches, STP sur la boucle, ping inter-VLAN routé.

## Critères de validation
- Quiz ≥ 70 %.
- TP vérifié par script (8 checks machine) : filtrage VLAN, access/trunk, pings
  intra et inter-VLAN, STP actif et boucle coupée. Note poussée dans Moodle.
