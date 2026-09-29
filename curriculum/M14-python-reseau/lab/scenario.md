# Labo M14 — Python pour le réseau : compléter `netcalc.py`

**Objectif** : implémenter les 4 fonctions de `/root/netcalc.py` sur le nœud
`dev` pour que la suite de tests pytest passe entièrement (6 tests).

Le kit de départ est déjà livré dans le nœud :

| Fichier | Rôle |
|---|---|
| `/root/netcalc.py` | squelette À COMPLÉTER (les 4 fonctions lèvent `NotImplementedError`) |
| `/root/test_netcalc.py` | tests pytest — NE PAS modifier |
| `http://127.0.0.1:8000` | petit serveur HTTP local (déjà lancé par le setup) |

## Les 4 fonctions à écrire

1. `cidr_hosts(prefix)` → `int` : nombre d'hôtes **utilisables**.
   Accepte un entier (`28` → 14) ou un CIDR en chaîne (`"10.0.0.0/24"` → 254).
   Formule : `2 ** (32 - prefix) - 2` (adresse réseau + broadcast retirées).
2. `first_usable(cidr)` → `str` : première adresse utilisable.
   Le module standard `ipaddress` fait tout : `ipaddress.ip_network(...).hosts()[0]`.
3. `mac_format(mac)` → `str` : normalise en `AA:BB:CC:DD:EE:FF` majuscules,
   en ignorant `-`, `.` et `:` (indice : `re.sub(r"[^0-9a-fA-F]", "", mac)`).
4. `http_get_status(url)` → `int` : GET via `urllib.request.urlopen(url)`,
   retourner `resp.status`. **Attention** : un 404 lève `urllib.error.HTTPError`
   — capture-la et retourne `err.code` (le test attend 404, pas une exception).

## Comment éditer

Utilise l'**Éditeur de fichiers** de la plateforme : nœud `dev`, chemin
`/root/netcalc.py`. (Ou `nano /root/netcalc.py` dans le terminal web.)

## Tester en continu

```bash
cd /root && python3 -m pytest -q test_netcalc.py          # toute la suite
python3 -c 'from netcalc import cidr_hosts; print(cidr_hosts("10.0.0.0/24"))'   # 254
python3 -c 'from netcalc import http_get_status; print(http_get_status("http://127.0.0.1:8000"))'  # 200
```

Quand `pytest` affiche `6 passed`, clique **Vérifier** (10 pts : 7 pour la
suite pytest, 1 par micro-check `cidr_hosts` / `first_usable` / `mac_format`).

## Pour aller plus loin (non noté)

- `paramiko`/`netmiko` (vus en cours) font la même idea qu'`http_get_status` :
  une boucle « requête → réponse → parsing » ;
- retourne plutôt un `dict` (code + corps) pour t'entraîner aux JSON (`jq`, `json.loads`).
