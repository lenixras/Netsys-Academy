# M14 — Python pour le réseau

## 1. Pourquoi Python côté réseau ?

Pendant des décennies, l'automatisation réseau s'est écrite en scripts shell
+ Expect. Ça marche, puis ça casse : le parsing devient opaque, les erreurs
sont muettes, aucun test possible. Python s'est imposé comme la lingua franca
de l'automatisation réseau pour trois raisons :

- **bibliothèque standard riche** : `ipaddress` (CIDR), `socket`,
  `urllib`/`http` (REST), `json`, `re`, `subprocess`, `logging` ;
- **écosystème dédié** : `netmiko`, `napalm`, `paramiko`, `scapy`, `ttp`,
  `pyats/nxpy` ;
- **qualité logicielle** : fonctions, types, exceptions et tests unitaires —
  un script réseau devient un module vérifiable (c'est exactement ce que fait
  le labo : 4 fonctions + 1 suite pytest).

## 2. Adressage : le module `ipaddress`

Tout calcul de sous-réseau propre passe par lui (revu conceptuellement en M8) :

```python
import ipaddress as ip
net = ip.ip_network("192.168.1.0/24")      # strict=True par défaut
net.network_address        # 192.168.1.0
net.broadcast_address      # 192.168.1.255
net.num_addresses          # 256
list(net.hosts())[0]       # 192.168.1.1  (première utilisable)
net.hosts()                # itérateur 254 adresses (ni réseau ni broadcast)
ip.ip_address("10.0.0.5") in net           # appartenance
sup = list(net.subnets(prefixlen_diff=1))  # découpe en /25
```

Le calcul manuel du nombre d'hôtes — `2**(32-prefixlen) - 2` — reste utile
pour comprendre d'où vient le nombre ; `hosts()` le matérialise. Attention
aux cas particuliers : /31 (lien, RFC 3074 → 2 utilisables, `hosts()` renvoie
les deux), /32 (hôte unique, `hosts()` est vide). Un code robuste les traite.

## 3. Parser des sorties texte : `re` et amis

Beaucoup d'équipements ne parlent que CLI. Récupérer un champ dans une sortie
`show` est un exercice de parsing, pas de bricolage :

```python
import re
m = re.search(r"Fast Ethernet address is (?P<mac>(?:[0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4})", out)
mac = m["mac"] if m else None       # dict d'accès nommé, propre
```

Bonnes pratiques :

- **regex nommées** (`(?P<nom>…)`) plutôt que des positions `\1 \2` fragiles ;
- **normaliser d'abord** : supprimer les séparateurs, mettre en majuscules —
  la fonction `mac_format` du labo applique exactement ce patron :
  `re.sub(r"[^0-9a-fA-F]", "", mac)` puis découpage tous les 2 caractères ;
- **toujours gérer l'absence de correspondance** (renvoyer `None` ou lever une
  exception explicite) : un `AttributeError: None has no group` en pleine
  campagne de collecte est le bug numéro 1 des scripts réseau ;
- pour les sorties tabulaires complexes, utiliser **ttp** ou **TextFSM** :
  des templates déclarent les motifs, le code ne fait que consommer des dicts.

## 4. API et HTTP : `urllib`, puis `requests`

Les équipements modernes exposent du REST (API Cisco, Junos RESTCONF,
programmatic Northbound). En standard library, `urllib.request` suffit pour
du GET simple :

```python
import urllib.request, urllib.error, json
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/devices", timeout=5) as r:
        data = json.load(r)
        status = r.status            # 200
except urllib.error.HTTPError as e:
    status = e.code                  # 404, 500 : c'est UNE réponse, pas un crash
except urllib.error.URLError as e:
    ...                              # connexion impossible (e.reason)
```

Point clé du labo : **HTTPError est une réponse HTTP** (avec un code). Une
fonction utilitaire qui renvoie le code doit l'attraper — sinon le test « le
serveur répond bien 404 sur cet objet absent » explose en exception. Toujours
mettre un `timeout` : une collecte sans timeout finira bloquée à 3h du matin.
Au-delà du GET, `requests` (sessions, auth, retry) devient plus agréable ; la
plate-forme d'examen n'installant que le standard, le labo reste en `urllib`.

## 5. SSH programmatique : `paramiko`, puis `netmiko`

`paramiko` implémente SSHv2 en pur Python :

```python
import paramiko
c = paramiko.SSHClient()
c.load_system_host_keys()
c.connect("10.15.0.2", username="root", key_filename="/root/.ssh/id_ed25519")
out = c.exec_command("ip -br addr")[1].read().decode()   # stdin, stdout, stderr
c.close()
```

`exec_command` convient aux commandes « one-shot ». Pour des équipements qui
tiennent un **shell interactif** (prompts, more, enable), `invoke_shell()`
ouvre un canal ; gérer les prompts soi-même est douloureux — c'est le métier
de **netmiko** :

```python
from netmiko import ConnectHandler
dev = {"device_type": "cisco_ios", "host": "10.15.0.2", ...}
with ConnectHandler(**dev) as conn:
    vlan = conn.send_command("show vlan", use_textfsm=True)  # déjà dict/list
```

Netmiko apporte : gestion des prompts par fournisseur, pagination automatique,
`send_config_set` avec diff optionnel, retries. Napalm pousse plus loin
l'abstraction multi-vendeur (données normalisées). Dans nos labs, les
équipements sont des nœuds Linux : on peut déjà s'entraîner avec paramiko
contre `sshd` — M15 (Ansible) utilise d'ailleurs SSH en sous-main, et M16
montre pourquoi on versionne tout ça.

## 6. Structurer et tester : le pattern du labo

Un module utile = fonctions courtes, documentées, typées, testées :

```python
def cidr_hosts(prefix: int | str) -> int:
    """Nombre d'hôtes utilisables pour un préfixe (24 ou '10.0.0.0/24')."""
```

`pytest` découvre les `test_*.py`, exécute chaque `test_*` et rapporte :
échec = une `assert` fausse ou une exception non levée… ou **une exception qui
remonte** (le squelette `NotImplementedError` fait exactement échouer les tests
de façon lisible). Avantages du mode « micro-checks + suite pytest » du labo :

- la suite (7 pts) prouve la cohérence globale ;
- les 3 micro-checks (1 pt chacun) donnent du feedback granulaire et empêchent
  de « tricher » en patchant un seul test.

Pour vos scripts de prod, le même réflexe : `python3 -m pytest -q`, tests en
face des fonctions, jamais de `print()` de debug comme seule validation.

## 7. Boîte à outils récapitulative

| Tâche | Outil |
|---|---|
| calcul IPv4/IPv6 | `ipaddress` |
| parsing CLI | `re` nommées, `ttp`, TextFSM |
| REST/HTTP | `urllib.request` (stdlib), `requests` |
| SSH one-shot | `paramiko` |
| shell interactif multi-vendeur | `netmiko`, `napalm` |
| sniff/génération de paquets | `scapy` (cf. M7) |
| exécuter une commande locale | `subprocess.run(..., capture_output=True)` |
| config/structuration | `yaml`/`json`, dataclasses |
| tests | `pytest` |
| logs et diagnostics | `logging` (niveaux, jamais print) |

## 8. Limites et pièges

- **états partiels** : une collecte qui échoue au 40ᵉ équipement sur 100 doit être
  reprise, pas relancée à zéro → idempotence et checkpointing ;
- **concurrence** : thread/`asyncio` pour collecter vite, mais attention aux
  sessions SSH partagées (paramiko n'est pas thread-safe par connexion) ;
- **secrets** : jamais de mot de passe en clair dans le code — variables
  d'environnement, secrets du launcher (cf. docs plateforme) ;
- **versions d'OS réseau** : les sorties CLI changent entre versions ; les
  templates de parsing doivent être versionnés et testés comme du code (M16).

## Références

- Docs Python : `ipaddress`, `urllib.request`, `re`.
- Kirk Byers, *The Practical Python Networking Lab* ; Netmiko/Paramiko docs.
- RFC 3074 (lien /31), cours M8 pour la théorie du découpage.
