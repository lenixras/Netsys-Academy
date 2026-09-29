# Brancher Moodle

Moodle n'est pas déployé par ce dépôt (produit tiers, GPL-3.0, PHP+MariaDB). Une fois
Moodle installé (docker `bitnami/moodle` ou LAMP classique) :

## 1. Service web externe
Site admin → *Avancé / Web services / Manuel d'installation de services* →
activer **REST**, ajouter un service `netsys` avec les fonctions :
- `core_grades_update_grades`
- `core_users_get_users_by_field`

Rôle : donner `moodle/grade:update` (et `moodle/user:viewdetails`) au rôle service.

## 2. Jeton + variables d'environnement du launcher
*Intégrations / Services web / Utilisateur de service* → générer un token pour un
compte `netsys-push` :

```bash
export MOODLE_URL=https://moodle.interne
export MOODLE_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
export MOODLE_COURSE_ID=3
```

Sans ces variables, les scores restent dans `var/scores/*.json` (format identique).

## 3. Correspondance des identités
Le `user` du launcher (pseudo de login) doit être le **username Moodle** de l'apprenant
(résolu via `core_users_get_users_by_field`). Avec un SSO LDAP/OIDC Moodle, aligner les
pseudo-labos sur les usernames.

## 4. Item de note
`moodle.py` envoie l'itemname `TP M5` (etc.) : créer une note de cours manuelle portant
ce nom dans le livre des notes, ou laisser Moodle créer l'item au premier push
(grade item « modifiable »).

## 5. Verrouillage de la roadmap (côté Moodle)
Chaque module = une activité quiz dont la *restriction d'accès* est « note ≥ 70 % du
quiz précédent » ; le lien vers le labo (`http://launcher:8090/lab/M5`) est une ressource
dans la section. La roadmap M0→M17 devient native Moodle ; le launcher ne fait que
pousser les notes de TP.
