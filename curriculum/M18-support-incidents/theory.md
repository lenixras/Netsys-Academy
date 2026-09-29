# M18 — Gérer un incident de service (support N1/N2)

## Objectifs

À la fin de ce module tu sais :
- dérouler une **méthode d'incident** : constater, isoler chaque maillon, corriger, valider ;
- diagnostiquer une panne **DNS** (zone obsolète, resolv.conf fantôme) ;
- diagnostiquer une panne **web** (process mort) et **DHCP** (pool sur le mauvais sous-réseau) ;
- rédiger un post-mortem compréhensible par un utilisateur non technique.

## Le principe : un incident = une chaîne de maillons

Un service perçu comme « cassé » n'est presque jamais cassé partout :

```text
utilisateur → résolution du nom → routage → port à l'écoute → application → données
```

La méthode consiste à **tester un maillon à la fois**, du point de l'utilisateur vers le
serveur, avec l'outil qui parle à ce maillon :

| Symptôme | Outil de diagnostic | Ce qu'il prouve |
|---|---|---|
| « le nom ne répond pas » | `dig @DNS nom +short` | zone DNS correcte ou non |
| « le site est mort » | `ss -tln \| grep :80` | le process écoute vraiment |
| « plus de connexion » | `ping IP` puis `dhclient` | DHCP/L3 vs application |

## Les pannes classiques après une migration

Une migration change des adresses ; tout ce qui les a mémorisées devient faux :

1. **Zone DNS obsolète** — l'enregistrement `A` pointe encore l'ancienne machine.
   Le DNS répond *bien*… avec une réponse morte. C'est le plus vicieux : pas de
   timeout, juste la mauvaise IP.
2. **resolv.conf fantôme** — le client interroge un serveur DNS disparu. Là, ça
   *hang* : chaque résolution attend le timeout. Confusion fréquente avec « le
   réseau est lent ».
3. **Pool DHCP sur le mauvais sous-réseau** — invisible tant qu'aucun client ne
   renouvelle son bail. Des semaines après la migration, un portable fraîchement
   installé reste sans adresse.
4. **Service jamais relancé** — les conteneurs/serveurs ne connaissent pas
   systemd ici : un process mort reste mort tant que quelqu'un ne le relance pas.

## Recharger une zone bind

`named` lit le fichier de zone **au démarrage** et au `reload`. Sans augmenter le
**serial**, un DNS secondaire garderait l'ancienne version ; ici on relance
directement `named`, donc le serial sert surtout à tracer la version.

## Clôture

Un ticket se ferme avec la **preuve de bout en bout** (`curl http://nom`) pas avec
« j'ai redémarré, ça devrait aller ». Le post-mortem répond à : quoi (symptôme
utilisateur), pourquoi (cause racine), comment (correctif), et quand (horodatage).
