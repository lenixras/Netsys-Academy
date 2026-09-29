# M10 — Observabilité réseau

Vague 3. Prérequis : M3 (Linux administrateur), M6 (routage OSPF).

## Objectifs

- Comprendre les deux modèles de collecte : **tirer** (polling SNMP) et **pousser**
  (syslog, traps, sFlow/NetFlow).
- Lire une **OID**, naviguer dans un arbre **MIB**, distinguer scalaires et tables.
- Démarrer et sécuriser un **agent SNMP v2c**, savoir ce que SNMP v3 ajoute.
- Construire une chaîne de logs : émission (`logger`), transport (UDP 514),
  collection, rotation, et corrélation avec un `tcpdump`.
- Relier ces briques à un atelier de supervision réel (sondes, seuils, alertes).

## 1. Pourquoi l'observabilité est un module à part

Un réseau « marche » n'est pas un réseau exploitable. L'exploitant doit répondre à quatre
questions en permanence : *quoi* est cassé, *depuis quand*, *quel impact*, *qui
prévenir*. Cela exige des données collectées en continu, pas des inspections ponctuelles.
On sépare classiquement :

- les **métriques** (valeurs numériques dans le temps : octets/s, utilisation CPU,
  température, pertes de paquets) — SNMP, sFlow/NetFlow, IPFIX ;
- les **logs** (événements textuels horodatés : interface up/down, authentification
  refusée, erreur optique) — syslog, journaux noyau, journaux applicatifs ;
- les **traces** (chemin d'une requête à travers les services) — plus pertinent pour les
  applications que pour les équipements, mais le même esprit.

Les trois alimentent un même outil : la sonde (Zabbix, Prometheus + exporters, LibreNMS,
Grafana Loki côté logs). Le lab M10 reconstruit manuellement le minimum de chaque chaîne,
pour que les abstractions de la sonde ne soient jamais magiques.

## 2. SNMP : architecture

SNMP (Simple Network Management Protocol, RFC 3411 et suivants) met en face un
**manager** (la sonde) et des **agents** (l'equipement monitoré), au-dessus d'UDP :

| Port | Sens | Usage |
|---|---|---|
| UDP/161 | manager → agent | GET, GETNEXT, GETBULK, SET |
| UDP/162 | agent → manager | TRAP / INFORM (notification poussée) |

Un agent expose une vue arborescente de son état : la **MIB** (Management Information
Base). Le manager lit (ou écrit) des noeuds identifiés par une **OID**.

### 2.1 OID et MIB

Une OID est une suite d'entiers séparés par des points, dans un arbre géré par l'IANA :

```
.iso(1).org(3).dod(6).internet(1).mgmt(2).mib-2(1) .system(1).sysContact(4).0
1 . 3 . 6 . 1 . 2 . 1                                  . 1 . 4 . 0
```

- `1.3.6.1.2.1` = **mib-2**, la MIB standard (RFC 1213) : `system`, `interfaces`,
  `ip`, `tcp`, `udp`, `snmp`.
- `1.3.6.1.4.1` = **enterprises** : les MIB éditeurs (Cisco, Juniper, NET-SNMP…).
- Un objet **scalaire** porte un sous-identifiant final `.0` (`sysUpTime.0`).
- Un objet **colonne** est indexé par une clé de table : `ifDescr.<ifIndex>`,
  et une table entière se parcourt par `walk`.

Cas d'usage typiques en exploitation :

```bash
snmpwalk -v2c -c COMM <dev> system            # identité de l'équipement
snmpwalk -v2c -c COMM <dev> 1.3.6.1.2.1.2.2.1.2   # ifDescr : la liste des interfaces
snmpget  -v2c -c COMM <dev> ifName.2
snmpstatus -v2c -c COMM <dev>                # résume uptime, contact, load
```

`snmpwalk` utilise les opérations GETNEXT : l'agent renvoie l'objet suivant dans l'ordre
lexicographique, ce qui permet de parcourir une table sans la connaître à l'avance.
`snmpbulkwalk` (GETBULK) accélère le parcours sur les grosses tables, mais peut noyer un
equipement peu puissant — d'où les limites de débit des sondes.

### 2.2 v1, v2c, v3

- **v1** : le premier standard, types de données limités, erreurs approximatives.
- **v2c** : ajoute GETBULK, de meilleurs codes d'erreur, et la notion de *counter64*
  (indispensable au-delà de 1 Gbit/s : un compteur 32 bits boucle en quelques secondes).
  Authentification = **communauté** en clair (`public`, `private`, ou la vôtre).
- **v3** : sécurité réelle — `authPriv` avec HMAC-MD5/SHA1/SHA-256 pour
  l'authentification et DES/AES-128/192/256 pour le chiffrement, gestion par
  utilisateur (`usm`) et non par communauté globale.

En production, SNMP v2c ne doit être accessible que depuis le réseau de management, avec
une communauté non triviale, idéalement restreinte par source (`rocommunity COMM 10.0.0.5`)
et en lecture seule. Sinon, SNMP v3 ou un accès via NETCONF/RESTCONF (TLS) remplace
avantageusement le GET SNMP.

Un agent `net-snmp` sous Linux se pilote par fichier de configuration :

```
agentAddress udp:161,udp6:[::1]:161
rocommunity  netsys               # lecture seule
rwcommunity  netsys-ro 127.0.0.1  # écriture, locale seulement
sysContact   noc-netsys@example.org
view   all    included  .1
access internet "" any noauth exact all none none
extend check-ospf /usr/local/bin/ospf-neighbors.sh   # OID personnalisée
pass .1.3.6.1.4.1.99999.1 /usr/bin/printf STRING hello-m10
```

`extend` et `pass` sont la porte de sortie « scriptable » de SNMP : exposer une métrique
métier (nombre de voisins OSPF Full, âge du dernier backup, résultat d'un ping interne)
sans écrire de sous-agent.

## 3. Logs : syslog et collection centralisée

Syslog (RFC 3164 en pratique, RFC 5424 pour le format structuré) est un flux de lignes
horodatées préfixées par une **priorité** `<PRI>` calculée depuis une *facility* (auth,
kern, daemon, local0…local7) et une *severity* (0 emerg → 7 debug) :

```
<134>1 2026-09-28T09:12:44+02:00 agent labo10 - - - TESTMSG
```

Chaîne complète :

1. **émission** — une application écrit dans `/dev/log` (socket unix), ou envoie un
   datagramme UDP : `logger -n 10.10.100.2 -P 514 -t ma-tags "message"` ;
2. **transport** — UDP/514 par défaut (léger, non fiable : en cas de saturation, on perd
   des lignes), TCP/514 ou TLS/6514 (RFC 5425/6587) quand la perte est inacceptable ;
3. **réception / filtration** — `rsyslogd` ou `syslog-ng` sur le collecteur, avec des
   règles *facility.severity → fichier*, rotation par `logrotate` ;
4. **indexation / interrogation** — Loki, Elasticsearch, ou simplement `grep`/`journalctl`.

Le lab M10 remplace l'étape 3 par un collecteur de 8 lignes en Python (ou `nc -u -l`) :
c'est exactement ce que fait `rsyslogd`, sans la rotation ni les filtres. On constate
alors trois pièges classiques : UDP non fiable (le message parti avant l'écoute n'arrive
jamais), absence d'horodatage de l'émetteur si on ne met pas `-i`/`-t`, et disque plein
si rien ne rotate. Un équipement réseau bien configuré envoie lui-même ses événements
(`logging host 10.10.100.2` sur un switch, `snmp-server host ... traps` pour les
notifications) : sinon l'incident ne laisse aucune trace exploitable.

## 4. sFlow / NetFlow : l'observabilité du flux

SNMP répond « combien de trafic sur cette interface », pas « qui parle à qui ». Les
technologies de flux complètent le tableau :

- **NetFlow / IPFIX** (Cisco, IETF) : l'équipement *observe* chaque flux (5-tuple), tient
  une table de flux actifs et exporte périodiquement les entrées closes. Exhaustif, mais
  coûteux en mémoire et en CPU sur l'équipement.
- **sFlow** (RFC 3196) : *échantillonnage* — 1 paquet sur N (p. ex. 1024) plus une
  mesure de compteur toutes les X secondes, exportés vers un collecteur. Sur un cœur à
  100 Gbit/s, c'est la seule approche tenable : le débit estimé = débit observé × N.
- **IPFIX/PSAMP** : la normalisation IETF de ces exports, et **mirror/SPAN** ou
  **tap** pour capturer réellement les paquets (analyse ponctuelle avec tcpdump/tshark,
  pas de l'historique).

Un atelier d'observabilité réseau sérieux combine donc : SNMP (état et volumétrie des
interfaces), syslog (événements), sFlow/NetFlow (topologie des flux), et un outil de
synthèse (Grafana) avec des **seuils** et des **alertes** dédupliquées.

## 5. Bonnes pratiques d'un plan de supervision

- **Un réseau de management dédié** (VLAN hors-band ou hors-production), pour que la
  supervision survive à un incident de trafic.
- **Read-only par défaut** : n'exposer les SET SNMP que sur des OID précises.
- **Horodatage et source** : NTP/chrony avant tout (sans horloge juste, corréler deux
  journaux est impossible — cf. M12), tag d'équipement sur chaque ligne de log.
- **Fréquence de polling cohérente** avec l'alerte voulue : un GET toutes les 5 min ne
  verra jamais une micro-coupure ; les compteurs 32 bits saturent au-delà de ~1 Gbit/s
  (utiliser `ifHCInOctets`, sous-arbre `ifXTable`).
- **Métriques d'usage, pas seulement d'état** : `rate(ifHCInOctets[1m])`, erreurs
  CRC (`ifInErrors`), discard, occupation de table FDB/ARP, voisinage OSPF/BGP.
- **Boucle fermée** : chaque seuil doit déboucher sur une action (ticket, page, script
  de contournement), sinon on produit du bruit et plus personne ne lit les alertes.

## Labo

`lab/scenario.md` — 2 nœuds (`agent` monitoré, `sonde`/`mon` collectrice) sur
`netsys/labnode:2`, lien direct 10.10.100.0/24. L'apprenant configure l'adressage, écrit
un `snmpd.conf` (communauté de lecture `netsys`, `sysContact`, OID personnalisée par
`extend`), démarre snmpd à la main, puis met en place une collection syslog UDP/514 et
vérifie tout depuis `mon` avec `snmpget`/`snmpwalk`/`grep`.

## Critères de validation

- Quiz ≥ 70 %.
- TP vérifié par script (7 checks machine, 10 points) : processus snmpd vivant,
  connectivité IP du lien d'observabilité, lecture de `sysDescr` et du `sysContact` avec
  la communauté `netsys`, ifTable non vide, écouteur UDP/514 actif, message `TESTMSG`
  archivé dans `/root/syslog.log`. Note poussée dans Moodle (ou `var/scores/`).
