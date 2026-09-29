# Architecture

## Vue générale (rappel de la specs)

```
[ÉLÈVE — navigateur]
   Moodle (cours, quiz, compétences)  ←—(optionnel, non déployé ici)————┐
        │ liens LTI / URL directes par module                           │ notes TP
        ▼                                                               │
Launcher netsys-academy (FastAPI, CE dépôt)                             │
  ├── sessions SQLite + TTL + purge orphelins                           │
  ├── containerlab deploy/destroy  ← labs M5-M7 (conteneurs FRR/Linux) ─┘
  ├── terminal web WebSocket (docker exec PTY + xterm.js)
  ├── checker (checks.yaml via docker exec) → JSON score → moodle.py
  └── drills (labs sans conteneur, ex. M8)
```

## Le launcher (`launcher/`)

| Fichier | Rôle |
|---|---|
| `app.py` | routes FastAPI (pages + API sessions + WS terminal) |
| `registry.py` | découvre `curriculum/M*/module.yaml` (statut skeleton/full, mode du lab) |
| `sessions.py` | SQLite `var/sessions.sqlite3`, TTL, sweeper, `gc_orphans()` au boot |
| `runner.py` | subprocess `containerlab deploy/destroy`, `--name session-<user>-<lab>` |
| `terminal.py` | WebSocket ↔ PTY `docker exec` (SDK docker) |
| `checker.py` | exécute `lab/checks.yaml` : `docker exec <nœud> cmd` + regex → score |
| `drills.py` + `M8/lab/check.py` | labs sans conteneur : correction déterministe |
| `moodle.py` | REST `core_grades_update_grades` si env Moodle, sinon `var/scores/*.json` |

## Décisions

1. **Les labs vivent dans le dossier du module** (`curriculum/M5-*/lab/`) : chaque module
   = contenu + labo + validation en un dossier Git autonome, publiable séparément
   (Note de sélection de la specs).
2. **Checks orchestés depuis l'hôte, exécutés dans les nœuds** : évaluer une topologie
   exige une vue multi-nœuds ; `docker exec` garde la commande « vue du terrain »
   (`vtysh`, `bridge vlan`, ping inter-nœuds qui traverse réellement le réseau).
3. **Terminal intégré plutôt que ttyd** : une seule écoute, auth par cookie déjà en place,
   keepalive réel pour le TTL, zéro allocation de ports. `ttyd` reste un branchement
   possible si un déploiement le préfère.
4. **Identité = pseudo + cookie signé** (`NETSYS_SECRET`). Colonne `auth_provider='local'`
   : en production, remplacer par SSO/OIDC ou launchpad LTI Moodle ; seul `user` compte
   en aval (nom de session, note poussée).
5. **Orphelins** : containerlab survit au launcher (conteneurs Docker). Au démarrage,
   tout lab `session-*` sans ligne `running` en base est détruit (`--gc` CLI aussi).
6. **RAM** : `NETSYS_MAX_SESSIONS=2` par défaut sur un petit hôte ; les topologies fixent
   des limites mémoire par nœud si besoin.

## Cycle de vie d'une session

launch → `containerlab deploy` (état `running`) → activité HTTP/WS = `touch` (TTL)
→ vérifications multiples (idempotentes) → destroy (manuelle, TTL écoulé, ou purge
au boot si crash).

## Branchement Moodle

Voir `moodle-setup.md`. Sans Moodle, les scores restent dans `var/scores/` — le format
JSON `{lab, user, score, max, checks[]}` est celui qui sera poussé.
