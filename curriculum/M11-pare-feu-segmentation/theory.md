# M11 — Pare-feu & segmentation

Vague 3. Prérequis : M1 (modèle OSI), M3 (Linux administrateur), M6 (routage).

## Objectifs

- Placer un filtrage de paquets au bon endroit dans la pile réseau (chaînes, hooks).
- Opposer filtrage *sans état* (iptables historique, ACL d'état) et pare-feu *à états*.
- Découper un réseau en **zones** (de confiance / non de confiance / DMZ) et traduire une
  politique en règles.
- Comprendre NAT, **SNAT/masquerade** et **DNAT/redirection de port**, et le rôle de
  conntrack.
- Écrire, tester et archiver un jeu de règles avec **nftables**, l'alternative moderne à
  iptables et le moteur utilisé par les distributions actuelles.

## 1. Où filtre-t-on ?

Un hôte ou un routeur Linux traverse plusieurs points de décision pour chaque paquet.
Netfilter expose cinq points d'accroche (*hooks*) :

| Hook | Quand | Usage |
|---|---|---|
| `prerouting` | dès l'arrivée, avant routage | DNAT (changer la destination) |
| `input` | destination = la machine elle-même | protéger l'équipement (SSH, SNMP, DNS) |
| `forward` | la machine relaie vers un autre port | le cœur du pare-feu routeur |
| `output` | générée par la machine | contrôler les sorties |
| `postrouting` | après routage, avant départ | SNAT / masquerade |

Le point crucial est que **`input` et `forward` ne sont pas la même histoire** : un
equipement peut être parfaitement joignable et empêcher tout transit, et inversement. Un
pare-feu entre deux zones travaille principalement dans `forward` (+ les deux hooks NAT),
tandis qu'un durcissement d'hôte (module M12) travaille dans `input`.

Le routage détermine aussi le hook : c'est la **table de routage** qui décide si un paquet
va en `input` (adresse locale) ou en `forward`. Sans `net.ipv4.ip_forward=1`, le paquet
destiné à autrui est simplement rejeté — une erreur classique quand « le pare-feu ne
laisse rien passer alors que les règles sont bonnes ».

## 2. Sans état vs à états

Un filtrage *stateless* examine chaque paquet isolément : pour autoriser un service, il
faut ouvrir le port dans les deux sens, souvent `0.0.0.0/0 ANY` côté retour, ce qui
revient à laisser entrer des paquets forgés.

Un pare-feu *stateful* tient une **table de connexions** (conntrack) et connaît l'état de
chaque flux (`new`, `established`, `related`, `untracked`). La politique devient
minuscule et sûre :

```
ct state established,related accept      # les retours sont toujours admis
ct state invalid drop                   # paquets hors de tout flux connu
iifname <wan> ip protocol icmp drop      # mais pas d'initiative depuis l'extérieur
iifname <lan> accept                     # le LAN initie ce qu'il veut
```

`related` mérite une attention particulière : il couvre les canaux annexes négociés à
l'intérieur d'un flux autorisé — la réponse UDP d'une `traceroute` ICMP, les connexions
de données FTP en mode actif, etc. Sans ce mot-clé, des diagnostics « marchent d'un côté
mais pas de l'autre ».

Conséquence directe pour le lab : la règle qui autorise les retours doit être **placée
avant** la règle qui bloque l'ICMP entrant, sinon la réponse à un ping sortant est jetée
(parce qu'elle arrive bien sur l'interface WAN). C'est la première source de
« mon pare-feu est cassé » : nftables évalue **dans l'ordre**, premier match gagnant.

## 3. NAT

Le NAT réécrit les adresses d'un paquet, dans deux tables/hooks distincts :

- **SNAT / masquerade** (hook `postrouting`) : change la *source*. `masquerade` est un
  SNAT dont l'adresse est prise dynamiquement sur l'interface sortante — celui des boxes
  ADSL et des conteneurs. Il permet à un réseau privé (RFC 1918) de sortir avec une seule
  adresse publique : le **NAPT** ajoute la réécriture des ports, d'où la nécessité d'un
  suivi d'état.
- **DNAT / port forwarding** (hook `prerouting`) : change la *destination*. Publier
  `fw:8080 → serveur:80` est une DNAT. Le client, lui, ne voit que l'adresse du pare-feu.

Trois pièges classiques :

1. **Le retour doit revenir par le pare-feu.** Une DNAT sans route de retour (ou un
   serveur dont la passerelle n'est pas le pare-feu) produit une connexion qui s'établit
   puis se coupe — le « asymmetric routing ».
2. **Le NAT ne rend pas compte du trafic chiffré** : les en-têtes applicatifs (FTP,
   SIP, H.323) contiennent des adresses IP ; il faut les *helpers* de conntrack, ou
   préférer le mode passif/le proxy applicatif.
3. **NAT ≠ sécurité.** C'est un contournement de la pénurie d'adresses ; seul le filtrage
   de la politique protège. Retirer la règle NAT d'un LAN le rend injoignable mais pas
   plus sûr.

Historiquement, `iptables` (IPv4) et `ip6tables` (IPv6) tenaient des jeux séparés ; la
famille `inet` de nftables les unifie dans une même table et une même chaîne.

## 4. nftables : tables, chaînes, sets

`iptables` empilait des règles dans des chaînes préexistantes, avec une relecture complète
à chaque insertion (coût linéaire, fenêtres de trafic non filtré). `nftables` remplace
iptables, ip6tables, arptables et ebtables par un seul outil et un seul jeu :

```
table inet filter {                # une table par famille, un nom libre
    set ssh_clients { type ipv4_addr ; elements = { 10.10.110.5, 10.10.110.6 } }
    chain input {
        type filter hook input priority 0 ; policy drop ;   # politique par défaut
        ct state established,related accept
        iifname "eth1" tcp dport 22 accept
        ip protocol icmp icmp type echo-request accept
        counter drop               # compter ce qui est jeté, pour l'audit
    }
}
```

Concepts à retenir :

- **table** (`inet`, `ip`, `ip6`, `bridge`, `arp`, `netdev`) + **chaîne** (hook +
  priorité + *policy* par défaut) + **règle** (correspondances → action
  `accept`/`drop`/`reject`/`log`/`count`/`ct set …`/`dnat`/`masquerade`).
- Les **sets** sont des ensembles typés (adresses, ports, interfaces) consultables en O(1) :
  la version moderne d'une « ACL d'une centaine de lignes », et la base de règles
  dynamiques (bannissement par fail2ban par exemple).
- Un **map/verdict map** autorise une décision par clé (`tcp dport vmap { 22 : accept,
  80 : accept }`) : une seule règle remplace dix.
- `nft list ruleset` est le reflet exact de l'état actif ; `nft -f fichier` recharge un
  jeu complet de façon atomique ; `nft monitor trace` + `meta nftrace set 1` suivent le
  chemin d'un paquet.

À l'ancienne, on écrivait `-A FORWARD -i eth1 -o eth2 -m state --state ESTABLISHED,RELATED
-j ACCEPT` ; la sémantique est identique, la syntaxe et la performance ne sont plus.

## 5. Zones et segmentation

Un pare-feu n'a de sens que dans une **politique de segmentation** :

| Zone | Confiance | Exemple de politique |
|---|---|---|
| `lan` / `trust` | interne | sort vers tout, initie ce qu'on publie |
| `wan` / `untrust` | extérieur | entrant uniquement ce qui est publié (DNAT) |
| `dmz` | semi-fiable | servi par le WAN, n'accède au LAN que sur quelques ports |

Le lab M10→M11 suit ce fil : le VLAN (M5) et le routage (M6) *séparent* les domaines de
diffusion et les sous-réseaux ; le pare-feu *décide* du droit de passage entre eux. Un
plan cohérent combine les deux : un VLAN par zone, une passerelle unique par zone, et une
politique qui ne parle que d'interfaces/zone, jamais d'adresses éparpillées.

Sur un NGFW open source (OPNsense/pfSense, VyOS, FortiGate, Juniper SRX, Cisco FTD), on
retrouve exactement les mêmes briques, habillées en GUI : interface → zone → policy →
NAT, avec le suivi d'état en commun et des objets (adresse de groupe, service de groupe)
comme les `sets` de nftables.

## 6. Vérifier, diagnostiquer, documenter

- `nft list chain inet filter forward` : ordre exact des règles (le premier match gagne).
- `nft list ruleset | grep counter` : quelles règles tombent vraiment ; une règle avec
  `counter packets 0` n'est jamais atteinte.
- `/proc/net/nf_conntrack` : les flux vus par le noyau, avec les adresses *avant/après*
  translation — le meilleur endroit pour comprendre un NAT.
- `tcpdump -ni eth1` puis `-ni eth2` **de part et d'autre** du pare-feu : voir le paquet
  arriver d'un côté et pas de l'autre localise immédiatement la règle qui le tue.
- `iptables -L -v` / `ebtables`/`arptables` ne montrent **pas** les règles nftables : ne
  pas se fier à un outil vide.
- Un jeu de règles est du code : versionner `/etc/nftables.conf` (ou le fichier chargé),
  tester en mode « compter sans jeter » avant de déployer, et garder une règle de secours
  (SSH autorisé depuis le LAN) pour ne pas se couper de la machine qu'on durcit.

## Labo

`lab/scenario.md` — 3 nœuds (`lan`, `fw`, `wan`) sur `netsys/labnode:2`, deux segments
10.10.110.0/24 et 10.10.120.0/24. L'apprenant active le transit, écrit un jeu nftables à
zones (policy drop, retours `established,related`), met en place le masquerade, bloque
l'ICMP entrant depuis la WAN, publie `wan:8080 → lan:80` par DNAT, puis archive le jeu
actif dans `/root/nft.conf.set`.

## Critères de validation

- Quiz ≥ 70 %.
- TP vérifié par script (7 checks machine, 10 points) : `ip_forward` actif, ping LAN → WAN
  à 0 % de perte (preuve du NAT), ping WAN → LAN échouant (blocage ICMP), `curl` sur le
  port publié renvoyant 200 (DNAT), règle `masquerade` présente, règle de drop ICMP
  entrante présente, jeu de règles archivé dans `/root/nft.conf.set`.
