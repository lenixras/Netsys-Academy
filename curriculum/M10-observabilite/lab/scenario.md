# Labo M10 — Observabilité : SNMP et collection de logs

**Objectif** : rendre `agent` observable depuis `mon` (le poste de supervision) avec
SNMP v2c (communauté de lecture, MIB standard, OID personnalisé) et mettre en place une
collection de logs syslog en UDP. À la fin, `mon` doit pouvoir lire l'inventaire réseau
d'`agent` (ifTable) et son contact, et archiver ses messages syslog.

Cliquez sur un nœud de la topologie pour ouvrir son **terminal** ; l'**Éditeur de
configuration** (en haut à droite) écrit directement un fichier dans le nœud choisi —
parfait pour `/root/snmpd.conf` ou `/root/collect.py`. Cliquez sur **Vérifier** pour
faire passer les checks machine (10 points).

## Plan d'adressage (à configurer vous-même)

| Nœud | Interface | Adresse | Rôle |
|---|---|---|---|
| agent | eth1 | 10.10.100.1/24 | hôte monitoré (snmpd, syslog) |
| mon | eth1 | 10.10.100.2/24 | sonde / collecteur |

## Étape 1 — Connectivité du lien d'observabilité

```bash
# sur agent :
ip link set eth1 up && ip addr add 10.10.100.1/24 dev eth1
# sur mon :
ip link set eth1 up && ip addr add 10.10.100.2/24 dev eth1
# depuis mon :
ping -c2 10.10.100.1
```

## Étape 2 — SNMP v2c sur agent

Utilisez l'éditeur (nœud `agent`, chemin `/root/snmpd.conf`) pour créer un fichier de
configuration minimal — on ne touche pas au `/etc/snmp/snmpd.conf` de la distribution :

```
agentAddress udp:161
rocommunity netsys
sysLocation Labo M10 - salle réseau
sysContact noc-netsys@lab10.local
```

Lancez l'agent SNMP **à la main** (pas de systemd dans l'image) :

```bash
snmpd -f -Lo -C -c /root/snmpd.conf > /root/snmpd.log 2>&1 &
ss -uln | grep 161          # l'agent écoute
tail -5 /root/snmpd.log     # en cas de refus de démarrage
```

> `rocommunity` = communauté de **lecture** seulement. En SNMP v3 on remplacerait cela
> par un utilisateur authentifié (MD5/SHA) et chiffré (AES) : la communauté v2c circule
> en clair, c'est un identifiant, pas un secret.

## Étape 3 — Interroger depuis mon

```bash
# NB : l'image du lab ne contient pas les fichiers MIB (licence Debian) →
# on utilise les OID numériques : sysDescr=.1.3.6.1.2.1.1.1, sysContact=.1.3.6.1.2.1.1.4,
# sous-arbre system=.1.3.6.1.2.1.1
snmpget  -v2c -c netsys 10.10.100.1 1.3.6.1.2.1.1.1.0
snmpget  -v2c -c netsys -Ov 10.10.100.1 1.3.6.1.2.1.1.4.0     # doit contenir « netsys »
snmpwalk -v2c -c netsys 10.10.100.1 1.3.6.1.2.1.1
snmpwalk -v2c -c netsys 10.10.100.1 1.3.6.1.2.1.2.2.1.2  # ifDescr : inventaire des interfaces
snmpstatus -v2c -c netsys 10.10.100.1
```

Avec un `snmpwalk ... ifTable` vide, votre supervision n'existerait pas : c'est la table
des interfaces (RFC 1213 / IF-MIB) qui permet de calculer les octets in/out, l'état
`up/down` et de générer des alertes.

## Étape 4 — (approfondissement) exposer un OID personnalisé

Ajoutez dans `/root/snmpd.conf` une extension, redémarrez snmpd et interrogez-la :

```
extend labnote /bin/echo supervision-m10-ok
```

```bash
snmpwalk -v2c -c netsys 10.10.100.1 1.3.6.1.4.1.8072.1.3.2   # NET-SNMP-EXTEND-MIB
```

> Étape non notée : si l'agent refuse le token `extend` (build minimal), retirez-le et
> repartez de l'étape 2 — seule la communauté et le `sysContact` sont vérifiés.

## Étape 5 — Syslog : collecteur sur mon, émission sur agent

`rsyslogd` n'est pas installé : on écrit son propre collecteur UDP/514. Deux options.

Option A — un script (éditeur, nœud `mon`, chemin `/root/collect.py`) :

```python
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 514))
f = open("/root/syslog.log", "ab", 0)
while True:
    f.write(s.recvfrom(2048)[0] + b"\n")
```

```bash
nohup python3 /root/collect.py > /dev/null 2>&1 &
ss -uln | grep 514
```

Option B — filet unique avec netcat, si `nc` est présent dans l'image :

```bash
nc -u -k -l -p 514 >> /root/syslog.log 2>/dev/null &
```

Le check accepte n'importe quel collecteur pourvu qu'il écoute en UDP/514 et archive les
lignes dans `/root/syslog.log`.

Puis, **sur agent**, envoyez le message de test exigé par le check :

```bash
logger -n 10.10.100.2 -P 514 -t labo10 "TESTMSG"
logger -n 10.10.100.2 -P 514 -t labo10 "lien d'observabilite operationnel"
```

Contrôles croisés depuis `mon` : `cat /root/syslog.log`, et sous `tcpdump` le message
RFC 3164 complet : `tcpdump -ni eth1 udp port 514`.

## Étape 6 — Bilan

| Question | Commande de vérification |
|---|---|
| L'agent SNMP répond-il ? | `snmpwalk -v2c -c netsys 10.10.100.1 1.3.6.1.2.1.1` |
| Quel est son contact ? | `snmpget -v2c -c netsys -Ov 10.10.100.1 1.3.6.1.2.1.1.4.0` |
| Combien d'interfaces vues ? | `snmpwalk -v2c -c netsys 10.10.100.1 1.3.6.1.2.1.2.2.1.2 \| wc -l` |
| Les logs arrivent-ils ? | `grep -c TESTMSG /root/syslog.log` |

Cliquez **Vérifier** : les 7 checks (10 points) valident la communauté SNMP, le contact,
la ifTable, l'écouteur UDP/514 et le message archivé.
