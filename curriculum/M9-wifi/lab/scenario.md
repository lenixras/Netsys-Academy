# Labo M9 — Plan d'implantation Wi-Fi (drills, sans conteneur)

L'hôte du labo (WSL2) n'a pas de radio simulée (mac80211_hwsim absent) : ce module se
joue **sans conteneurs**, en exercices de planification statiques. Les 12 énoncés sont
les mêmes pour tout le monde ; les formules de calcul sont données dans chaque énoncé —
aucune connaissance implicite n'est exigée, une calculateur suffit.

## Consignes

1. Ouvre le formulaire de l'onglet labo : 12 questions (cellules, canaux, SNR,
   capacité, adressage VLAN, sécurité/roaming).
2. Réponds question par question. Réponses numériques en **ASCII** (moins `-89`,
   point décimal `.`), un seul nombre ou un seul token quand l'énoncé le demande.
3. Quand tout est rempli, clique **Vérifier** : score sur 12, la correction affiche
   la valeur attendue pour chaque question manquée.

## En ligne de commande (hors plateforme)

```bash
python3 curriculum/M9-wifi/lab/check.py alice          # affiche les 12 questions
python3 curriculum/M9-wifi/lab/check.py alice rep.json # corrige le JSON de réponses
```

Format de `rep.json` : `{ "cell1": "34", "snr1": "25", ... }` (id -> réponse).
