# M0 — Comment marche Internet

Vague 0. Prérequis : aucun.

## Objectifs
- Expliquer le modèle client/serveur et le rôle de chaque acteur d'une session web.
- Distinguer adresse privée / adresse publique et comprendre le NAT.
- Décrire la chaîne de résolution DNS (récursive côté client, itérative côté résolveur).
- Comprendre ce qu'est un paquet, une adresse MAC, une adresse IP, un MTU.
- Relier une requête « j'ouvre https://exemple.fr » aux couches IP, TCP, TLS, HTTP.
- Observer son propre réseau avec `ip`, `arp`, `dig`/`getent`, `traceroute`.

## Théorie

### 1. Le réseau des réseaux
Internet n'est pas un réseau unique : c'est une interconnexion de réseaux
autonomes (fournisseurs d'accès, entreprises, datacenters) qui parlent tous le
même langage : la suite TCP/IP. Chaque réseau est identifié par un numéro
d'AS (Autonomous System) et les réseaux se connectent entre eux pour s'échanger
du trafic. Un paquet traverse souvent 10 à 15 de ces réseaux (« hops ») entre
votre machine et un serveur distant.

Le principe fondamental : les machines ne se parlent que par adresses IP.
Les noms (exemple.fr) ne sont qu'une commodité humaine, résolue par le DNS.

### 2. L'unité de base : le paquet
Sur un réseau, tout est découpé en **paquets**, des blocs binaires de taille
bornée, et chaque paquet voyage « encapsulé » comme une poupée russe :

- une **trame Ethernet** (couche 2) : adresses MAC source/destination + type ;
- à l'intérieur, un **datagramme IP** (couche 3) : adresses IPv4 source et
  destination, protocole transport, et un **TTL** (nombre max de routeurs
  traversés, décrémenté à chaque saut) ;
- à l'intérieur, un segment **TCP** (ports, numéros de séquence, fenêtre de
  réception) ou un datagramme **UDP** (ports, sans garantie de remise) ;
- et enfin les **données** de l'application (page HTTP, requête DNS…).

Chaque équipement ne lit que l'en-tête de sa couche : le switch regarde la MAC,
le routeur regarde l'IP, le serveur web lit le TCP. On ne « parle » jamais
directement à l'autre bout : on empile des en-têtes au départ, on les dépile à
l'arrivée. C'est la **superposition (stack)**, et la trame est recréée à chaque
routeur — seule l'IP de bout en bout reste la même (avant NAT).

### 3. Client et serveur
Une communication réseau est presque toujours un dialogue client/serveur :
- le **client** initie la connexion et consomme un service (navigateur, app mail) ;
- le **serveur** écoute en permanence sur un **port** (numéro 0–65535) et répond.

Quelques ports bien connus à retenir :
| Port | Service |
|------|---------|
| 22   | SSH     |
| 25/587 | SMTP  |
| 53   | DNS (surtout UDP) |
| 80   | HTTP    |
| 123  | NTP (UDP) |
| 443  | HTTPS (HTTP sur TLS) |

Une connexion TCP est initiée par la **poignée de main** SYN → SYN-ACK → ACK.
Elle est caractérisée par le tuple (IP source, port source, IP dest, port dest,
protocole) : la « socket », ce que montrent `ss -tunap` ou Wireshark plus tard.
« Client/serveur » est un **rôle**, pas une machine : un serveur web devient
client DNS quand il résout un nom, et `curl` est un client HTTP.

### 4. Deux adresses, deux rôles
- **Adresse MAC** (48 bits, ex. `aa:bb:cc:dd:ee:ff`) : inscrite dans la carte
  réseau, elle n'a de sens que sur le **segment local**. Elle change à chaque
  nœud intermédiaire du chemin.
- **Adresse IPv4** (32 bits, ex. `10.198.8.2/24`) : logique et hiérarchique,
  elle identifie l'interface ET son réseau. Le préfixe `/24` (masque
  255.255.255.0) découpe l'adresse en partie réseau + partie hôte :
  `10.198.8.0/24` contient 256 adresses, dont 254 utilisables par des hôtes
  (la première est l'adresse réseau, la dernière le broadcast).

La règle d'or du routage sur une machine : la destination appartient-elle à un
de mes préfixes **connectés** ? Alors envoi direct (on demande sa MAC par ARP).
Sinon, envoi à la **passerelle par défaut**, le « next-hop » qui connaît la
suite du chemin. On le voit avec `ip route show default`.

**ARP** (Address Resolution Protocol) fait le pont entre les deux mondes :
« qui a l'IP 10.198.8.1 ? Réponds ta MAC » (diffusion sur le segment, réponse
unicast). Les réponses sont stockées dans un **cache ARP** consultable avec
`arp -a` ou `ip neigh` — c'est ce cache que le TP vous fait observer.

### 5. Adressage IP : public vs privé
Les adresses IPv4 sont rares. La RFC 1918 réserve trois plages **privées**,
jamais routées sur Internet, utilisables en interne sans location :
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

Votre box attribue à vos machines une adresse privée (souvent `192.168.x.x`
via DHCP). Seule la box possède une adresse **publique** (fournie par l'ISP,
parfois dynamiquement). C'est le pont entre les deux mondes.

### 6. Le rôle du routeur, puis du NAT
Un routeur ne fait qu'une chose : consulter une **table de routage**, choisir
le prochain saut (« next-hop ») selon l'IP de destination (la route la plus
spécifique), décrémenter le TTL, recréer la trame avec une nouvelle MAC et
transmettre. Chez vous :
- le PC a une route par défaut (`default via 192.168.1.1`) : « si je ne sais
  pas, j'envoie à la box » ;
- la box a une route par défaut vers l'ISP ;
- sur Internet, les opérateurs échangent leurs routes via **BGP**.

Le **NAT** (Network Address Translation, RFC 2663/3022) permet à plusieurs
machines privées de partager une seule adresse publique. La variante la plus
courante est le **NAPT** (ou « MASQUERADE ») : la box réécrit l'IP source ET
le port source, et mémorise la correspondance dans une table de translation :

```
192.168.1.10:52314  →  88.77.66.55:31000   (vers 93.184.216.34:443)
```

Quand la réponse revient, la box consulte sa table et renvoie le paquet au bon
client interne. Conséquences pédagogiques :
- un service interne n'est pas joignable depuis Internet sans **redirection de port** ;
- le NAT casse le modèle bout-en-bout : c'est pour cela qu'IPv6 le rend inutile ;
- les tables NAT ont une taille finie et un timeout : les connexions trop
  longues sans trafic peuvent être coupées (d'où les keepalive TCP/App) ;
- sans le vouloir, le NAT agit aussi comme un pare-feu basique : rien n'entre
  s'il n'a pas été demandé.

Et le TTL dans tout ça ? Quand il atteint 0, le paquet meurt et le routeur
renvoie une erreur ICMP « Time Exceeded ». **traceroute** exploite ce
mécanisme : envoyer des paquets avec TTL 1, 2, 3… pour faire parler chaque
saut du chemin et le lister.

### 7. DNS : l'annuaire en cascade
Le DNS (Domain Name System, RFC 1034/1035) est une base de données
hiérarchique et distribuée. Résoudre `www.exemple.fr` :
1. l'application consulte `/etc/hosts` (fichier local), puis interroge le
   **résolveur** indiqué dans `/etc/resolv.conf` (celui de la box, `1.1.1.1`,
   `8.8.8.8`… — dans le labo, c'est le DNS interne de Docker) ;
2. le client pose une question **récursive** au résolveur : « trouve l'IP et
   réponds-moi la valeur finale » ;
3. le résolveur, lui, fait des questions **itératives** : il interroge les
   serveurs **racine** (`.`), qui renvoient les TLD (`.fr`, `.com`), qui
   renvoient les serveurs **faisant autorité** pour le domaine, qui donnent
   enfin l'enregistrement demandé ;
4. chaque réponse est **mise en cache** selon son TTL, pour ne pas repartir
   de la racine à chaque requête.

Sens des enregistrements utiles : **A** (nom → IPv4), **AAAA** (→ IPv6),
**CNAME** (alias), **MX** (mail), **NS** (serveurs du domaine), **PTR**
(IP → nom, la résolution inverse).

Commandes d'observation : `getent hosts NOM` (résolution complète, cache +
hosts + DNS), `dig NOM` (la chaîne en clair), `dig @1.1.1.1 NOM` (forcer un
serveur), `dig +trace` (voir chaque étape itérative).

### 8. MTU et fragmentation
Chaque liaison a un **MTU** (Maximum Transmission Unit) : la taille maximale,
en octets, que sa trame peut transporter (1500 pour l'Ethernet standard, 1480
environ derrière certains accès DSL). Si un paquet IP est plus gros que le MTU
d'un maillon intermédiaire, il est **fragmenté** en plusieurs morceaux — sauf
si le bit « Don't Fragment » est positionné : alors le routeur renvoie une
erreur ICMP et **le path MTU discovery** permet à TCP de réduire la taille de
ses segments. Piège classique de dépannage : un MTU mal réglé casse les gros
transferts en silence alors que les petits pings passent. On le relève avec
`ip link show` ou `/sys/class/net/<iface>/mtu`.

### 9. Le trajet complet d'une requête web
Récapitulatif bout-en-bout de « j'ouvre https://exemple.fr » :
1. **DNS** : le navigateur demande l'IP de `exemple.fr` (hosts → cache →
   résolveur → racine/TLD/autoriaité) ;
2. **IP** : le paquet part vers la passerelle par défaut (MAC trouvée par
   ARP), la box (routeur + NAT) réécrit la source et transmet ;
3. **Routage** : chaque AS fait décroître le TTL et achemine (visible avec
   `traceroute`/`mtr`) ;
4. **TCP** : handshake SYN / SYN-ACK / ACK vers le port 443 ;
5. **TLS** : négociation de version, authentification du certificat, clés de
   session ;
6. **HTTP** : `GET /` chiffré dans TLS, réponse `200` avec le HTML ; puis le
   navigateur relance le cycle pour chaque image ou script (souvent d'autres
   noms → nouveau DNS) ;
7. à la fermeture, FIN TCP (ou abandon silencieux en keep-alive).

Chaque étape peut échouer, et chaque erreur a un diagnostic différent :
c'est tout l'enjeu des modules suivants.

## Bonnes pratiques / pièges
- **Ne pas confondre** : « Internet ne marche pas » ≠ « mon Wi-Fi ne marche pas ».
  Vérifier dans l'ordre : lien local → IP → passerelle → DNS → destination.
- Une adresse `169.254.x.x` (APIPA) signifie que le DHCP a échoué : le client
  s'est auto-attribué une adresse de secours, il n'a pas de route par défaut.
- Un `ping 8.8.8.8` qui passe mais `ping nom.fr` qui échoue = problème **DNS**,
  pas problème de routage.
- Ne pas diaboliser le NAT : c'est un outil ; mais connaître ses limites
  (pas d'entrée sans redirection, tables saturables, IPv6 preferred).
- Les `* * *` dans `traceroute` sont normaux : beaucoup d'opérateurs
  rate-limitent les ICMP de réponse ; une étoile ≠ une panne.
- Retenez l'ordre d'observation de votre propre machine : lien, adresse,
  route par défaut, cache ARP, resolv.conf, MTU. C'est la base de tout
  dépannage (module M13).

## TP — Observer son propre réseau (labo m0-observe)
Le labo de ce module ne casse rien : il vous fait **cartographier le réseau
vivant** de la machine `h1` du launcher (cliquez sur le nœud pour ouvrir son
terminal web). Six relevés à écrire dans `/root/obs/`, chacun vérifié
automatiquement contre l'état réel du nœud :
1. l'IPv4 de la **passerelle par défaut** → `gw_ipv4.txt` (`ip route show default`) ;
2. la **MAC** de cette passerelle, apprise via ARP → `gw_mac.txt` (`ping -c1 <gw>` puis `ip neigh`) ;
3. le **préfixe** de votre réseau de management → `mgmt_prefix.txt` (adresse + masque, puis `ip -4 route show scope link`) ;
4. la résolution du **nom interne inventé** `atelier.m0.internal` → `dns_atelier.txt` (`getent hosts`) ;
5. l'adresse du **résolveur** configuré → `resolver.txt` (`cat /etc/resolv.conf`) ;
6. le **MTU** de `eth0` → `mtu.txt` (`ip link show dev eth0`).

Cliquez sur **Vérifier** quand les six fichiers sont remplis (10 points).
Vous verifiez ainsi, sur des valeurs réelles, tout le parcours d'un paquet :
MAC (couche 2) → passerelle (routage) → résolveur (DNS) → MTU (liaison).

## Critères de validation
- Quiz ≥ 70 %.
- Labo M0 vérifié par les checks (10 points).
