# M22 — DNS avancé

## Le DNS n'est pas une base unique

Un nom n'est « possédé » que par ses **serveurs faisant autorité** (ici `auth`).
Tout le reste n'est que copie : cache, zone secondaire, ou délégation.

- **Type de zone chez BIND** : `master` (l'original), `slave` (copie par
  transfert AXFR), `forward` (on ne fait que relayer).
- **Transfert AXFR** : le secondaire demande « donne-moi la zone version N ».
  Le maitre refuse tout le monde par défaut (`allow-transfer { none; }`) —
  on ouvre uniquement vers les IP des secondaires.
- **Serial (SOA)** : changer un enregistrement **sans incrémenter le serial**
  = les secondaires ne rattrapent pas. C'est l'erreur de prod nº1 du DNS.
- **Zone inverse** (`in-addr.arpa`) : même mécanisme, sens inverse
  adresse → nom, indispensable pour le PTR (antispam, diagnostics).

## Et la « récursion » ?

Un serveur récursif (`recursion yes`) part des racines et suit les délégations
NS/glue pour vous. Pour un client, `rec` est « son DNS » ; `auth` est
« l'autorité du nom ». Ce lab vous fait jouer les deux rôles : secondaire
esclave de `auth`, et resolviseur interrogé par `cli`.

## Étapes du lab

1. `auth` : autoriser le transfert AXFR vers 10.22.1.2 (et recharger named).
2. `rec` : écrire `/root/named.conf` — options récursives (recursion yes,
   allow-recursion { any; }) + les deux zones `type slave` masters 10.22.1.1 —
   puis lancer named.
3. `cli` : `dig @10.22.0.2 web.lab22.local` et `dig @10.22.0.2 -x 10.22.0.99`.
