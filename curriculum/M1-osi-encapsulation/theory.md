# M1 — Modèle OSI & encapsulation

Vague 0. Prérequis : M0.

## Pourquoi un modèle en couches ?

Un réseau met d'accord des machines hétérogènes : câbles, cartes réseau, switches,
routeurs, serveurs, navigateurs. Plutôt qu'un protocole monolithique, on découpe le
problème en **couches** : chaque couche rend un service à la couche supérieure et
cache ses détails à celles d'en dessous. Deux modèles cohabitent dans le vocabulaire
professionnel :

- le modèle **OSI** (théorique, 7 couches, normalisé ISO) ;
- le modèle **TCP/IP** (pragmatique, 4 couches, celui réellement déployé).

| # OSI | Nom OSI | Rôle | Équivalent TCP/IP | Unité (PDU) | Exemples |
|---|---|---|---|---|---|
| 7 | Application | Interfaces et protocoles métiers | Application | Données | HTTP, DNS, SSH, SMTP |
| 6 | Présentation | Encodage, chiffrement, compression | Application | Données | TLS, JSON, JPEG |
| 5 | Session | Gestion des sessions/dialogues | Application | Données | RPC, NetBIOS |
| 4 | Transport | Fin de bout en bout, ports, fiabilité | Transport | Segment (TCP) / Datagramme (UDP) | TCP, UDP |
| 3 | Réseau | Adressage logique, meilleur chemin | Réseau | Paquet | IP, ICMP, OSPF |
| 2 | Liaison | Diffusion locale, trames, MAC | Accès réseau | Trame | Ethernet, Wi-Fi, ARP* |
| 1 | Physique | Bits, signaux, câbles | Accès réseau | Bits | cuivre, fibre, radio |

\* ARP est un cas particulier : protocole de résolution log→physique, souvent
placé en couche 2/3, et encapsulé directement dans Ethernet (type `0x0806`).

Retenez surtout la correspondance **ports ↔ couche 4, adresses IP ↔ couche 3,
adresses MAC ↔ couche 2** : c'est la triade que l'on lit dans toute capture.

## L'encapsulation, pas à pas

Quand une application envoie des données, chaque couche **ajoute son en-tête
(devant)** — parfois un en-tête ET un pied, comme la séquence de vérification
Ethernet (FCS) en fin de trame — puis passe le résultat à la couche inférieure :

```
Données applicatives            « GET / HTTP/1.1 »
+ en-tête HTTP/TLS       L7 →   message
+ en-tête TCP            L4 →   segment   (ports source/dest, numéros de séquence, drapeaux)
+ en-tête IPv4           L3 →   paquet    (IP src, IP dst, protocole 6, TTL, checksum)
+ en-tête Ethernet       L2 →   trame     (MAC dst, MAC src, type 0x0800)
+ préambule/FCS          L1 →   signal    (bits sur le câble)
```

À la réception, c'est la **décapsulation** symétrique : la carte vérifie la trame,
l'IP vérifie son en-tête, TCP réassemble, l'application lit ses octets. Un
intermédiaire ne lit jamais tout : le **switch** s'arrête à la couche 2 (il regarde
la MAC de destination), le **routeur** lit jusqu'à la couche 3 (l'IP), le
**serveur** voit enfin la couche 7. C'est la règle d'or du dépannage : plus on
monte, plus on a besoin que tout ce qui est en dessous fonctionne déjà.

Quelques tailles à connaître par cœur (sans options) :

- en-tête Ethernet : **14 octets** (6+6+2), plus 4 d'IFG + 12 de préambule/FCS hors trame ;
- en-tête IPv4 : **20 octets** minimum, le champ IHL (4 bits, valeur `5`) donne sa taille × 4 ;
- en-tête TCP : **20 octets** minimum, l'offset de données (valeur `0x50`) donne sa taille × 4 ;
- en-tête UDP : **8 octets** fixes ;
- en-tête ARP : **28 octets**, trame ARP complète = 42 octets.

## MTU, MSS et fragmentation

Ethernet transporte au plus **1500 octets** de charge utile par trame : c'est le
**MTU** (Maximum Transmission Unit), une limite de la couche 2. La couche 3 doit
s'y plier : soit elle **fragmente** le paquet IP en plusieurs morceaux (champ
Flags/Frag, bit `DF` pour « Don't Fragment »), soit — comportement moderne — on
laisse la **PMTUD** (Path MTU Discovery) découvrir le plus petit MTU du chemin et
on évite de fragmenter. Pour TCP, la bonne réponse est en amont : au handshake,
chaque côté annonce une fenêtre **MSS** (Maximum Segment Size) = MTU − 40
(20 IP + 20 TCP), donc typiquement 1460. Un « trou noir PMTU » (des paquets qui
passent mais pas les gros) vient presque toujours d'un ICMP « besoin de frag »
bloqué par un pare-feu.

## Les trois acteurs du labo : ARP, IP/TCP, DNS

**ARP (couche 2/3)** — « qui a 10.1.1.20 ? » est une requête **diffusée**
(MAC destination `ff:ff:ff:ff:ff:ff`) ; la réponse est **unicast**. Sans ARP, une
machine connaît l'IP de sa passerelle mais pas sa MAC, et aucune trame ne part.
Sur une capture, une requête ARP pèse 42 octets et ne transporte aucun port :
c'est la preuve vivante qu'on est sous la couche 3.

**Le handshake TCP (couche 4)** — trois trames, dans cet ordre :

1. `SYN` (drapeau `0x02`) : « ouvre une connexion, mon numéro de séquence initial est X » ;
2. `SYN/ACK` (`0x12`) : « reçu, voici le mien Y » ;
3. `ACK` (`0x10`) : « connecté ».

Les accusés de réception portent le numéro attendu (X+1, Y+1), et non le dernier
reçu : TCP accuse réception du **prochain** octet espéré. Une connexion qui n'atteint
pas `ESTABLISHED` a échoué au handshake — le `SYN` parti sans `SYN/ACK` renvoie
vers le serveur ou un pare-feu, le `SYN` jamais arrivé renvoie vers le routage
(couches 1–3).

**DNS (couche 7 sur UDP/53)** — requête et réponse partagent un **identifiant de
transaction** (16 bits) que le client choisit ; c'est ainsi qu'il fait faire
correspondance à la bonne question dans un flot de réponses UDP non fiable.
La question encode le nom en étiquettes de longueur (`3 www 6 netsys 4 test 0`),
le type `A` demande une address IPv4. Une réponse DNS typique est petite (< 512 o
en UDP historique), ce qui lui évite toute fragmentation : l'encapsulation est
aussi un exercice de dimensionnement.

## Lire une capture : tshark et Wireshark

Une capture est un fichier **pcap** : un en-tête global (magic `0xa1b2c3d4`,
version 2.4, type de liaison — 1 = Ethernet) puis, par paquet, un en-tête de
record (horodatage, taille capturée, taille réelle) et les octets bruts de la
trame. `Wireshark` est l'interface graphique de ces fichiers ; `tshark` en est le
moteur en ligne de commande, et l'outil de référence dans un terminal :

```bash
tshark -r capture.pcap                      # résumé : n° | temps | src > dst | protocole | info
tshark -r capture.pcap -V                   # arbre détaillé Frame→PHY→…→Application
tshark -r capture.pcap -x                   # hexdump brut (vérifier les octets soi-même)
tshark -r capture.pcap -Y 'tcp.flags.syn==1 && tcp.flags.ack==0'   # filtrer (display filter)
tshark -r capture.pcap -T fields -e ip.src -e tcp.dstport          # extraire des champs
```

Lecture reflexe d'une ligne de résumé TCP : `10.1.1.10:51234 → 10.1.1.20:80 [SYN] Seq=0
Win=65535` : adresses de couche 3, ports de couche 4, drapeau, séquence, fenêtre.
Le `-V` montre l'emboîture exacte — `Frame 1: 54 bytes on wire` puis
`Ethernet II`, `IPv4`, `Transmission Control Protocol` — et `frame.len` est la
taille sur le câble, à comparer au MTU.

## Ce que le labo vérifie

Dans le sandbox, trois mini-captures vous sont fournies (`/root/cap_*.pcap`).
Vous devez produire six artefacts dans `/root/resp/` — compte de SYN, compte de
SYN/ACK, séquence des drapeaux du handshake, taille d'une trame ARP, nom et
identifiant de la requête DNS. Chaque check **recalcule** la valeur avec tshark
sur la capture vivante : pas de réponse mémorisée, que de la lecture comprise.

## TCP ou UDP : deux contrats de transport

Les deux protocoles de couche 4 encapsulent des données dans le même en-tête IP
(champ protocole `6` ou `17`), mais leurs services diffèrent :

- **TCP** est fiable, ordonné, orienté connexion : handshake à 3 trames,
  accusés de réception, contrôle de fenêtre, retransmission. Sur une capture, on
  voit `[SYN]`, `[SYN, ACK]`, `[ACK]` puis des segments numérotés. C'est le choix
  de HTTP, SSH, SMTP — dès que chaque octet compte.
- **UDP** est au mieux effort, sans connexion : 8 octets d'en-tête, aucun
  handshake, aucune garantie. DNS l'utilise justement parce qu'une requête/réponse
  tient en un échange : perdre un paquet coûte un timeout et un retry, pas une
  connexion. Sur une capture UDP, il n'y a AUCUN signe de vie côté transport —
  la fiabilité est remontée dans le protocole applicatif (l'`dns.id` du labo en
  est l'exemple).

Retenez le prix de la fiabilité : le handshake TCP ajoute 1 aller-retour avant le
premier octet utile, et 3 trames minimum avant toute donnée applicative.

## Dépanner par les couches : la méthode diviser pour régner

L'ordre OSI n'est pas une coquetterie de cours, c'est un arbre de décision :

1. **Couche 1-2** : le lien est-il up ? Y a-t-il du trafic ? (`ip link`, LED, `tshark -i`)
2. **ARP** : la résolution log→phys aboutit-elle ? (`arping`, ou `ip neigh`)
3. **Couche 3** : le chemin IP existe-t-il ? (`ping`, `traceroute`)
4. **Couche 4** : le port est-il ouvert ? handshake aboutit-il ? (`nc -vz`, SYN sans réponse = pare-feu ou service absent)
5. **Couche 7** : le service répond-il correctement ? (le protocole métier lui-même)

Chaque strate qui échoue invalide les suivantes : inutile de tester HTTP si ARP
ne résout pas. C'est exactement ce que les captures du labo illustrent — ARP,
handshake TCP et DNS y sont les trois portes successives d'un simple clic.

## À retenir

- Une couche ne parle qu'à son homologue (principe de la couche) ; l'en-tête de
  l'expéditeur est lu par l'homologue du destinataire.
- Les adresses racontent la portée : MAC = domaine local, IP = bout en bout,
  port = processus.
- `frame.len` croît à chaque encapsulation ; la charge utile d'une couche est la
  trame entière de la suivante.
- MTU borne la couche 2, MSS borne TCP, la fragmentation est le plan B.
- ARP avant le premier paquet IP, handshake avant le premier octet applicatif,
  DNS avant la première URL tapée : trois rituels que toute capture montre.
