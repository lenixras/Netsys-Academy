# M4 — Services critiques : DNS, DHCP, NTP, SSH

Quatre services discrets mais vitaux : sans eux, un réseau « marche » à peine.
On les monte dans des conteneurs **sans systemd** : chaque démon se lance à la
main, ce qui est paradoxalement la meilleure façon de comprendre ce que fait
un « service ».

---

## 1. DNS — l'annuaire

### 1.1 Hierarchie et noms

DNS (Domain Name System, RFC 1034/1035) traduit un nom hiérarchique
(`web.lab4.local.`) en adresse IP. La hiérarchie est un arbre inversé :
racine `.` → TLD (`local` est ici un domaine privé, jamais publié sur
Internet) → zones déléguées. Chaque zone est un fichier texte authoritative
géré par une équipe, servie par des name-servers.

### 1.2 Records utiles

| Type | Rôle | Exemple |
|---|---|---|
| A | nom → IPv4 | `web IN A 10.1.41.10` |
| AAAA | nom → IPv6 | |
| NS | name-server autorisé pour la zone | `@ IN NS ns.lab4.local.` |
| SOA | en-tête de zone : serveur principal, serial, refresh/retry/expire/minimum TTL | |
| CNAME | alias | `www IN CNAME web` |
| PTR | IP → nom (résolution inverse, zone `in-addr.arpa`) | |

Le **serial** du SOA doit augmenter à chaque modification : c'est lui que les
serveurs secondaires comparent pour décider de re-transférer la zone (AXFR).

### 1.3 Résolution : récursif vs itératif

Le client (stub resolver, `dig`, libc) interroge en mode **récursif** son
résolveur (`/etc/resolv.conf`). Le résolveur, lui, accomplit le travail
**itératif** : racine → TLD → zone, en suivant les référents NS. BIND/named
est authoritative par défaut (`recursion no;`) : il ne répond que pour ses
zones, ce qui est la posture correcte pour un serveur interne — un serveur
récursif ouvert (open resolver) est une arme de réflexion d'attaque DDOS.

### 1.4 Configurer named sans systemd

Deux fichiers : `named.conf` (options + déclaration de zones) et le fichier
de zone. Vérification **avant** lancement : `named-checkconf`,
`named-checkzone`. Lancement foreground avec logs sur le terminal :
`named -c /root/named.conf -g &`. Écoutes : UDP/TCP 53. Tests :
`dig @10.1.40.1 web.lab4.local +short`, `dig axfr @10.1.40.1 lab4.local`
(doit être REFUSED — les transferts de zone sont restreints aux secondaires).

Pièges classiques de zone : oubli du point final sur les noms absolus
(`ns.lab4.local.`), serial figé, TTL excessif qui masque les corrections,
 `$TTL` manquant en tête de fichier.

---

## 2. DHCP — l'attribution automatique

### 2.1 DORA

DHCP (RFC 2131) prête une adresse pour une durée limitée (lease). Le
dialogue est un broadcast en quatre temps :

1. **DISCOVER** — client sans IP, source `0.0.0.0`, destination `255.255.255.255`, port 68→67 ;
2. **OFFER** — un serveur propose adresse + masque + passerelle + DNS ;
3. **REQUEST** — le client accepte (et l'annonce aux autres servers via le champ server-id) ;
4. **ACK** — le bail est confirmé et journalisé (base des leases).

Le client renouvelle à 50 % du bail (REQUEST unicast), sinon à 87,5 % ;
passé l'expiration l'adresse retourne au pool. C'est ce mécanisme de
renouvellement qui distingue DHCP d'un simple tirage au sort.

### 2.2 Options et pools

Les **options** (numérotées, DHCPv4) transportent le reste de la config :
1 = subnet mask, 3 = router (passerelle), 6 = DNS, 15 = domain name,
51 = durée du bail. Une plage est décrite par un *pool* :
`dhcp-range=10.1.40.100,10.1.40.150,255.255.255.0,8h` suivi de
`dhcp-option=3,10.1.40.254`.

### 2.3 dnsmasq, serveur léger

dnsmasq combine DNS caching et DHCP sur un seul binaire. Points de vigilance :
- il relie la plage DHCP au sous-réseau d'une interface existante (sinon il
  désactive silencieusement le range) ;
- `port=0` désactive sa fonction DNS — nécessaire quand named occupe déjà le 53 ;
- `dnsmasq --test` valide la syntaxe sans rien démarrer ;
- l'écoute se constate par `ss -uln | grep :67`.

Dans ce labo, aucune machine n'exécute un vrai client DHCP
(isc-dhcp-client/udhcpc absents de l'image) : on valide donc config + écoute,
ce qui est exactement la démarche d'un admin qui prépare son pool avant de
brancher les postes.

### 2.4 DHCP et relay

Un broadcast ne traverse pas un routeur : pour desservir le LAN 10.1.41.0/24
depuis `srv` (sur 10.1.40.0/24), il faudrait un `dhcp-relay` (option 82,
giaddr) sur `gw`, ou un dnsmasq par sous-réseau avec une interface sur
chaque VLAN. C'est la raison pour laquelle les gros networks placent souvent
le DHCP près du coeur avec relay, ou le répartissent par site.

---

## 3. NTP — l'horloge partagée

### 3.1 Pourquoi

Journaliser des événements sur dix machines sans horloge commune rend tout
corrélate impossible (logs, Kerberos tolère 5 min, certificats, métriques).
NTP synchronise les horloges avec une précision de la milliseconde sur un LAN.

### 3.2 Stratum et topologie

La source (stratum 0 : GPS, horloge atomique) alimente un serveur stratum 1,
qui en alimente d'autres (stratum 2, …, max 15). La règle d'or : ne pas
casser la chaîne (pas de boucle) et ne pas sync l'horloge sur elle-même.
`local stratum 10` dans chrony crée une référence de secours locale : sans
montée, le serveur annonce une heure « interne » au lieu de ne rien répondre.

### 3.3 L'algorithme en quatre horodatages

Un client envoie à t1, le serveur répond en horodatant t2, la réponse arrive
à t3 ; le client connaît t4 (son echo). Offset ≈ ((t2-t1)+(t3-t4))/2, retard ≈
(t4-t1)-(t3-t2). En répétant l'échantillonnage (polling), chrony fait une
régression sur les échantillons, trie les sources saines (`^*` = sélectionnée,
`^+` = concourante, `^-` = rejectée par le filtrage) et corrige **progressivement**
la pente ( slew ) plutôt qu'en sautant.

### 3.4 chrony en pratique

Serveur : `allow 10.1.40.0/24` autorise les clients (par défaut chrony n'écoute
rien du réseau) ; `local stratum 10` pour tenir seul. Client :
`server 10.1.40.1 minpoll 2 maxpoll 3` force un sondage rapide (4-8 s) — utile
en lab, agressif sur Internet. `chronyc -a makestep` force une correction
immédiate (les 3 premiers pas, grâce à `makestep 1.0 3`). Diagnostic :
`chronyc sources -v`, `chronyc tracking`.

---

## 4. SSH — la porte de secours propre

### 4.1 Deux facteurs, deux usages

sshd authentifie soit par **mot de passe**, soit par **couple de clés** (Ed25519
aujourd'hui). Le mot de passe est un secret partagé, rejouable, vulnérable à la
brute force : à proscrire pour les accès automatisés et à remplacer partout par
la clé. La clé publique est diffusible par nature ; le secret, c'est la clé
privée, qui ne quitte jamais le client (et idéalement protégée par une
passphrase).

### 4.2 authorized_keys, côté serveur

Le fichier `/home/<user>/.ssh/authorized_keys` liste les clés autorisées, une
par ligne (`ssh-ed25519 AAAA… commentaire`). La permission est **stricte** :
700 sur `.ssh`, 600 sur le fichier, propriété de l'utilisateur — sinon sshd
ignore silencieusement le fichier (paranoia `StrictModes`, active par défaut).
C'est un piège d'admin récurrent : la clé est « bien » collée, mais sshd
réclame un mot de passe.

### 4.3 Chaîne complète d'une connexion

Le client contacte le port 22, vérifie la **clé d'hôte** du serveur (première
connexion = TOFU, puis stockée dans `known_hosts`), négocie un secret de
session (échange de clés), puis prouve son identité (signature avec sa privée).
`ssh-keygen -A` génère les clés d'hôte manquantes sur un serveur neuf ;
`/run/sshd` doit exister pour le privilege separation sandbox.

### 4.4 Automatisation

`BatchMode=yes` interdit toute question interactive : la connexion échoue si
une clé n'est pas autorisée — comportement recherché ici (ni mot de passe, ni
sshpass : c'est la clé ou rien). `ConnectTimeout=5`,
`StrictHostKeyChecking=no` sont des options de test, pas de production.
Pour la prod : `PasswordAuthentication no`, `PermitRootLogin no`, clés + fail2ban.

---

## 5. Le fil rouge du labo

Les quatre services ne tournent que si le réseau **routé** est posé d'abord
(adresses statiques, passerelles, `net.ipv4.ip_forward=1` sur `gw`) : DNS
UDP depuis client1, chrony UDP, SSH TCP traversent tous le routeur. Ensuite,
l'ordre importe : named avant dnsmasq (guerre du port 53), chrony serveur
avant client (rien à interroger sinon), sshd avant toute connexion (évident).
Enfin, chaque service s'évalue par sa **surface observable** — `dig`,
`ss -uln`, `chronyc sources`, `ssh … hostname` — pas par « ça a l'air de
marcher » : c'est exactement la logique des checks de validation.

---

## 6. Aide-mémoire des commandes du labo

| Besoin | Commande |
|---|---|
| Valider named.conf / la zone | `named-checkconf /root/named.conf` ; `named-checkzone lab4.local /root/db.lab4.local` |
| Lancer named avec logs au terminal | `named -c /root/named.conf -g &` |
| Interroger un serveur précis | `dig @10.1.40.1 web.lab4.local +short` |
| Tester dnsmasq sans démarrer | `dnsmasq --test --conf-file=/root/dnsmasq.conf` |
| Vérifier l'écoute UDP 67 | `ss -uln` (filtrer la ligne `:67`) |
| Démarrer chrony (srv et client) | `chronyd -f /root/chrony.conf` |
| Forcer la correction immédiate | `chronyc -a makestep` |
| Voir l'état des sources | `chronyc -n sources` (`^*` sélectionnée, `^+` concourante, `^?` hors ligne) |
| Générer les clés d'hôte (1er boot) | `ssh-keygen -A` ; `mkdir -p /run/sshd` |
| Démarrer sshd | `/usr/sbin/sshd` |
| Paire client sans passphrase | `ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519` |
| Connexion test non interactive | `ssh -o BatchMode=yes -o StrictHostKeyChecking=no svc@10.1.40.1 hostname` |

Trois réflexes d'admin avant de chercher midi à quatorze heures :
l'interface est-elle **up avec la bonne adresse** ? le service écoute-t-il
(`ss -uln`/`ss -tln`) sur la **bonne IP/la passerelle** ? le chemin retour
passe-t-il par le **routeur** (`ip_forward=1`, `ip route` sur le serveur) ?
La majorité des « DNS ne répond pas » de ce labo sont en réalité des
« client1 n'a pas de route par défaut vers gw » ou des « srv n'a pas de route
retour vers 10.1.41.0/24 ».

