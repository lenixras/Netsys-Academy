# M13 — Dépannage structuré

Vague 3. Prérequis : M6 (routage), M7 (TCP et qualité de service), M10 (observabilité),
M11 (pare-feu).

## Objectifs

- Substituer une **démarche** au tâtonnement : décrire, délimiter, hypothèse, tester,
  corriger, vérifier, documenter.
- Savoir quelle commande appartient à quelle couche, et ce qu'elle prouve vraiment.
- Interpréter les silences (timeout) et les erreurs explicites (unreachable, refused).
- Repérer les pannes typiques d'un chemin IP : lien éteint, masque erroné, route
  manquante ou interceptrice, NAT/pare-feu, service qui n'écoute pas.
- Construire et dérouler une séquence de sondes ordonnée (L1 → L7) qui élimine
  une couche à chaque résultat, avant toute modification de configuration.
- Produire un post-mortem exploitable, et une mesure de prévention.

## 1. Le problème n'est pas technique, il est méthodologique

Un réseau moderne est un système à couches, chacun avec ses propres états : table ARP,
FIB, conntrack, file d'attente, boucle de retransmission TCP, configuration applicative.
L'erreur du débutant est de tester **le tout** (« est-ce que ça marche ? ») et de conclure
« ça ne marche pas ». La bonne question est toujours : *jusqu'où cela marche-t-il ?* Le
chemin le plus long à tracer, mais le plus rapide à diagnostiquer, est celui qui coupe
l'espace de recherche en deux à chaque test.

Trois règles pratiques :

1. **Un symptôme avant une cause** : relever la sortie exacte (message, compteur, horaire)
   avant de toucher quoi que ce soit. Toute modification non documentée détruit la scène.
2. **Un seul changement à la fois**, puis re-test du maillon concerné. Sinon on ne sait
   pas ce qui a réparé — et on ne sait pas ce qu'il faut reconfigurer au prochain incident.
3. **Revenir à la documentation** (schéma, plan d'adressage, DMZ, tables de VLAN) : un
   écart entre le documenté et le réel est une réponse, dans un sens comme dans l'autre.

## 2. La méthode en couches ( OSI / TCP-IP )

| Couche | Question | Outils Linux |
|---|---|---|
| 1 — support | Le lien est-il actif ? | `ip -br link`, `ethtool`, `dmesg` |
| 2 — liaison | MAC visibles ? VLAN/ARP corrects ? | `bridge fdb show`, `ip neigh`, `arping`, `tcpdump -e` |
| 3 — réseau | Adresse, masque, route, reachability | `ip -4 addr`, `ip route`, `ip route get`, `ping`, `tracepath`, `ip neigh` |
| 4 — transport | Port ouvert, session établie, pertes | `ss -tlnp`, `ss -tin`, `tcpdump -nn`, `iperf3` |
| 5-7 — service | Réponse applicable, DNS, authentification | `curl`, `dig`, journaux de l'application |

On descend rarement : on **monte à partir du point de rupture**. La couche 3 est le
carrefour : c'est là que l'on sait si le problème est local (ma configuration),
intermédiaire (un équipement sur le chemin) ou distant (le service).

### Le test de voisin direct

`ping <passerelle>` est le test le plus rentable du dépannage IP. Il valide en un paque
la couche 1 (lien up), la couche 2 (résolution ARP), la couche 3 locale (adresse, masque,
FIB connected) et la couche 3 du voisin (qui répond). S'il échoue, tout le reste est
inutile : on a une zone de panne minuscule.

### Délimiter par le milieu

Sur un chemin à N sauts, tester un point médian (le premier routeur, puis le deuxième)
divise l'espace de recherche. `tracepath` automatise ce découpage : il émet des paquets
avec un TTL croissant (sonde UDP en général sous Linux, ICMP sur d'autres systèmes), et
affiche le premier saut qui ne renvoie rien. Attention : `tracepath` ne distingue pas une
vraie panne d'un équipement qui ne génère tout simplement pas de TTL-expired (pare-feu
strict, cf. M11) — un trou au saut 4 n'implique pas que le saut 4 est cassé.

## 3. Lire les messages d'erreur

| Sortie | Signification | Cause typique |
|---|---|---|
| `Destination Host Unreachable` (émis par vous) | aucune route, ou ARP sans réponse | route manquante, câble/VLAN, masque erroné |
| `From <passerelle> icmp_seq=1 Destination Net Unreachable` | un routeur intermédiaire rejette | route absente, `blackhole`/`unreach`, policy de routage |
| `Request timeout` (rien ne revient) | paquet parti, réponse perdue | NAT/route de retour, pare-feu qui drop (M11), asymétrie |
| `100% packet loss` avec TTL dépassé | boucle de routage | deux routes statiques croisées |
| `Connection refused` | le paquet arrive, rien n'écoute | service down, écoute sur 127.0.0.1, port faux |
| `Connection timed out` en TCP | drop silencieux | filtrage, MTU (paquets trop grands, cf. M7) |
| `Network is unreachable` sur `ip route get` | la FIB refuse la destination | masque/route, `blackhole` |

La distinction **rejet explicite (ICMP / RST)** vs **silence (drop)** est structurante :
elle sépare un équipement qui refuse activement d'un équipement qui ne voit pas le paquet,
et donc un problème de *politique* d'un problème de *connectivité/routage*.

## 4. Panoramique des pannes classiques

- **Couche 1/2** : interface `DOWN` administrativement (`ip link set <if> down` oublié),
  port sans `LOWER_UP` (câble, VLAN non autorisé sur le trunk, spanning-tree en
  listening/discarding — M5), table FDB qui flashe, MAC clonée en double.
- **Adressage** : masque erroné (le cas le plus pernicieux, car le ping vers le voisin
  immédiat fonctionne), deux interfaces du même sous-réseau sur le même routeur sans
  `proxy_arp`, préfixe hors du plan documenté, `broadcast` absent.
- **Routage** : route de retour manquante (panne n°1 des labs !), `ip_forward=0`,
  route `blackhole` / `prohibit` / `unreach` injectée par un script ou un outil de
  routage dynamique, métrique qui rend une route moins préférée qu'une default, routes
  dynamiques qui tombent (voisin OSPF bloqué en ExStart — M6).
- **État/pare-feu** : politique `drop` qui ne laisse pas passer les retours, conntrack
  saturé (`nf_conntrack: table full` dans `dmesg`), NAT sans règle `masquerade`, helper
  FTP/ SIP mal configuré (M11).
- **Transport/service** : service lié à `127.0.0.1`, port déjà pris, fichier de
  configuration non rechargé, certificat expiré, DNS qui résout l'ancienne adresse
  (`dig +short`, TTL, cf. M4).
- **Performance** : MTU/PMTUD, file d'attente pleine, erreur CRC sur un seul sens
  (`ip -s link`), gigue et perte (M7).

## 5. Boîte à outils commentée

```bash
ip -br addr ; ip route show table all ; ip route get 10.13.3.20   # l'état déclaré
ip neigh ; bridge vlan show ; bridge link show                    # l'état L2
ss -tlnp ; ss -tin ; ss -s                                        # l'état transport
nft list ruleset ; cat /proc/net/nf_conntrack                     # l'état filtré
ping -c4 -W2 <cible> ; arping -I <if> <cible> ; tracepath <cible> # la mesure
tcpdump -ni <if> -nn icmp or tcp port 80                          # la vérité du fil
iperf3 -c <serveur> -t 10                                         # le débit réel
dmesg -T | tail ; journalctl -k -p warning                        # les traces noyau
```

`ip route get <dst>` est sous-estimé : il interroge la FIB **exactement comme le noyau**,
et renvoie l'interface, la passerelle et la source choisie. C'est la réponse définitive à
« vers où part vraiment ce paquet ? » — bien plus rapide que de lire dix routes.

`tcpdump` sur **deux interfaces** d'un équipement convertit une supposition en certitude :
si le paquet entre et ne sort pas, le problème est local (routage, filtrage, MTU) ; s'il
sort et ne revient pas, il est en aval ou dans la route de retour.

## 6. Documentation et prévention

Un dépannage réussi mais non documenté produira le même incident dans trois mois. Le
post-mortem tient en cinq lignes : **symptôme observé / cause racine / correction /
délai d'impact / mesure préventive**. Les mesures préventives appartiennent aux modules
suivants : supervision avec alertes sur l'état des interfaces et le voisinage (M10),
politique de pare-feu explicite et journalisée (M11), configuration versionnée et déployée
par outil (Ansible M15, IaC M16), tests de non-régression du plan d'adressage, et
*runbook* de routine pour chaque service (M12/M14).

Un bon indicateur d'une infrastructure mûre n'est pas l'absence d'incidents, mais le
temps moyen entre le signal d'alerte et la localisation de la cause — et le fait que la
même cause ne se reproduise jamais deux fois pour les mêmes raisons.

## Labo

`lab/scenario.md` — 4 nœuds en chaîne (`h1 – r1 – r2 – h2`, segments 10.13.1.0/24,
10.13.2.0/24, 10.13.3.0/24). Le launcher applique l'adressage nominal puis **injecte
trois pannes simultanées** que l'apprenant doit trouver une par une, en respectant
l'ordre des couches, et réparer pour rétablir le ping de bout en bout.

## Critères de validation

- Quiz ≥ 70 %.
- TP vérifié par script (4 checks machine, 10 points) : interface `eth1` de `r2` à l'état
  `UP`, adresse `10.13.3.20/24` sur `h2`, route de `r1` vers 10.13.3.0/24 bien directionnelle
  (`ip route get` → `via 10.13.2.2`), et `ping -c4` de `h1` vers `h2` à 0 % de perte.
- Post-mortem rédigé dans `/root/postmortem.md` (non notifié automatiquement).
