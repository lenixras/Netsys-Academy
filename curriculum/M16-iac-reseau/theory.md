# M16 — Infrastructure as Code réseau

## 1. L'IaC en une phrase

Traiter l'infrastructure comme du logiciel : **la description de l'état cible
vit dans du code, versionné, relu, testé, déployé automatiquement** — et la
config des machines n'est plus jamais la source de vérité. Le corollaire qui
change tout : une config « d'exception », patchée à la main un dimanche soir,
n'existe pas en IaC — soit elle est dans le dépôt, soit elle est une
dérive à corriger.

Pour un réseau, l'IaC couvre trois couches :

1. **le plan** (topologies, adressage, VLANs) — fichiers YAML/HCL versionnés ;
2. **la convergence** (Ansible M15, scripts Python M14, controllers
   GLAPI/DNAC) — le code qui applique le plan ;
3. **la vérification** (linters, tests, drift detection) — le code qui prouve
   que le réel matche le plan.

Le labo M16 travaille les couches 1 et 3 : un fichier de topologie cassé, un
linter, Git pour l'historique.

## 2. Pourquoi Git est la pierre angulaire

Git apporte exactement ce qui manquait aux répertoires `backup/configs/` :

- **historique** : `git log`, `git show`, `git blame` — qui a changé quoi,
  quand et pourquoi (le message de commit) ;
- **rollback** : `git revert` d'un commit de config restaure le plan ;
- **revue** : une *pull request* force la relecture avant application —
  le « quatre-yeux » devient un contrôle technique, pas une faveur ;
- **branchements** : on expérimente sur une branche, on ne casse jamais `main` ;
- **clé d'unicité** : la topologie, le playbook et les tests vivent dans le
  même dépôt et évoluent ensemble.

Un flux minimal et réaliste (le « trunk-based » des équipes réseau récentes) :

```bash
git switch -c tpmgmt-202          # une branche par changement
# éditer, linter, tester
git add -A && git commit -m "fix topo"
git push                          # → CI lance lint + tests
# revue, merge sur main → déploiement depuis main
```

En labo (comme dans M12), la branche `main` locale suffit : l'essentiel est
le réflexe **éditer → valider → committer**, avec un message qui raconte
l'intention (`fix topo`, pas `update`).

## 3. containerlab comme plan d'infrastructure

`containerlab` (utilisé par toute la plateforme) lit une topologie YAML :

```yaml
name: m16-design
topology:
  nodes:
    r1: { kind: linux, image: netsys/labnode:2 }
  links:
    - endpoints: ["r1:eth1", "r2:eth1"]
```

Ce fichier est de la même famille que ceux que produisent les outillages
« design → déploiement » (Terraform pour le cloud, Nornir+inventaires pour le
réseau, eem/CloudInit…). Les erreurs y sont typiques et **statiques** — donc
détectables sans déployer : nœud référencé mais absent, interface inventée,
lien bouclé sur lui-même, doublon de lien, image oubliée. Un déploiement
raté coûte des minutes et des conteneurs orphelins ; un linter, une seconde.

## 4. Écrire son propre validateur : le pattern `lint.py`

Le labo livre `lint.py` (~60 lignes, stdlib + PyYAML). Son architecture est
celle de tout outil de validation :

1. **parser** le format (échec → erreur de syntaxe, stop) ;
2. **extraire le modèle** (nœuds, liens, endpoints) ;
3. **appliquer des règles** indépendantes, **cumuler les erreurs** avec un
   message situé (`lien 1: noeud inconnu r9`) ;
4. **rendre un verdict** : exit 0 = conforme, exit ≠ 0 = non conforme.

Le point 4 est le contrat qui permet de brancher l'outil dans une chaîne :
`&&`, scripts CI, gate de déploiement. Un validateur qui jase mais sort 0 est
pire qu'absence de validateur. Les équivalents professionnels :
`containerlab verify`, `batfish`, `yamllint`,
`ansible-lint`, `terraform validate`, `confd`/`yanglint` pour YANG.

## 5. La CI réseau : du lint au déploiement

Le pipeline complet d'un changement de config réseau :

```
PR → lint YAML → tests unitaires (variables, plans d'addr) →
     validation topo (lint.py / clab dry-run) →
     déploiement sur banc → tests d'intégration (ping, BGP up,
     vérifications M14 en pytest) → merge + déploiement prod (Ansible)
```

Deux idées à retenir :

- **fail fast** : les erreurs bon marché (syntaxe, références) doivent remonter
  avant toute commande sur un équipement ;
- **le pipeline est le déploiement** : plus aucun humain ne tape `ansible-playbook`
  en prod ; il *merge* une PR, et le robot applique. Les checks de la plateforme
  (ce que fait le bouton **Vérifier**) sont exactement ce principe, à l'échelle
  d'un labo.

## 6. Dérive (drift) et inventaire

L'IaC ne vaut que si le réel reste aligné. D'où deux rituels :

- **drift detection** : rejouer périodiquement en `--check` (Ansible) ou
  comparer l'état lu (Python/napalm) au plan versionné ; une alarme, pas un
  silence ;
- **inventaire canonique** : la source unique des adresses/noms (netbox,
  tableau versionné, `group_vars/`) alimente topologies ET playbooks — si
  l'inventaire est faux, tout l'IaC est faux.

## 7. Bonnes pratiques d'un dépôt d'infra

- un commit = une intention (`fix topo`, `add link r3-sw1`) ;
- messages de commit en impératif, lisibles dans `git log --oneline` ;
- **arbre de travail propre** : `git status --porcelain` vide — rien ne doit
  traîner hors versionnement (les checks du labo le vérifient) ;
- séparer données/logique (variables d'environnement hors des playbooks) ;
- README ou spec qui dit « à quoi doit ressembler le résultat » — le `spec.md`
  du labo joue ce rôle, comme un *definition of done* ;
- secrets jamais dans Git (cf. vault Ansible M15, variables d'env, fichiers
  d'inventaire chiffrés).

## 8. Ce que vérifie le labo

Sur le dépôt `/root/lab` du nœud `dev2` :

1. `lint.py topo.yaml` sort 0 (5 pts) — les 3 erreurs du fichier livré sont
   corrigées ;
2. un commit dont le message contient `fix` (2 pts) — l'histoire Git raconte
   la correction ;
3. le lien `r3:eth2` du plan cible existe (1 pt) et `r9` a disparu (1 pt) ;
4. arbre de travail propre : `git status --porcelain` vide (1 pt) — la
   correction est *versionnée*, pas seulement appliquée.

Notez la philosophie d'évaluation, commune à tous les labs système : on ne
vous demande pas d'affirmer que c'est bon, on **constate l'état** — c'est
déjà de la drift-detection.

## Références

- Docs containerlab (topology spec, `verify`).
- *Infrastructure as Code* (Spraul, O'Reilly) ; blog ScalingPython sur GitOps.
- RFC 2119/… pour les messages de commit : *How to Write a Git Commit Message* (Chris Beams).
