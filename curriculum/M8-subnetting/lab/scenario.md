# Labo M8 — Drills de subnetting

12 exercices tirés selon ton pseudo (mêmes exercices à chaque visite).
Calcule avec `ipcalc`, Python (`import ipaddress`) ou à la main — la correction est
machine, déterministe.

Exemples de consignes :
- *Adresse réseau de 10.23.67.180/26* → `10.23.67.128`
- *Nombre d'hôtes dans 192.168.13.0/20* → `4094`
- *Plus petit préfixe pour 500 hôtes* → `23`
- *Sous-réseau /64 n°5 de 2001:db8:a42::/48* → `2001:db8:a42:5::`

Quand tes réponses sont saisies, clique **Vérifier** : score sur 12.
En ligne de commande (hors plateforme) :

```bash
python3 curriculum/M8-subnetting/lab/check.py alice      # affiche les questions
python3 curriculum/M8-subnetting/lab/check.py alice rep.json   # corrige
```
