# Labo M16 — IaC réseau : réparer une topologie Git-gérée

**Objectif** : sur le nœud `dev2`, le dépôt `/root/lab` contient une topologie
containerlab **cassée** (3 erreurs), un linter (`lint.py`) et le plan cible
(`spec.md`). Toi : éditer → linter → commiter, comme dans un vrai workflow GitOps.

## Point de départ

```bash
ls /root/lab           # topo.yaml (cassé), lint.py, spec.md
git -C /root/lab log --oneline         # 1 commit "import-initial"
cat /root/lab/spec.md  # le plan FINAL à rétablir
python3 /root/lab/lint.py /root/lab/topo.yaml   # liste les 3 erreurs (exit 1)
```

Les erreurs typiques : un nœud sans `image:`, un lien vers un nœud fantôme
(`r9`), un lien dont les deux bouts sont identiques. La spec impose aussi un
4ᵉ lien (`r3:eth2 ↔ sw1:eth2`) absent du fichier cassé.

## Étape 1 — Corriger topo.yaml

Utilise l'**Éditeur de fichiers** de la plateforme : nœud `dev2`, chemin
`/root/lab/topo.yaml`. Compare avec le YAML attendu de `spec.md` (indentation
2 espaces, `endpoints: ["a:ethX", "b:ethY"]`).

## Étape 2 — Linter jusqu'à OK

```bash
python3 /root/lab/lint.py /root/lab/topo.yaml
```

Doit afficher `lint: OK` (exit 0). Le linter vérifie : `name` présent, image
sur chaque nœud, endpoints qui désignent des nœuds existants, deux bouts
distincts, pas de liens en double.

## Étape 3 — Committer

```bash
git -C /root/lab status --porcelain    # montre le diff en attente
git -C /root/lab add -A
git -C /root/lab commit -m "fix topo"
git -C /root/lab log --oneline
```

L'identité git est déjà configurée dans le dépôt. `git status --porcelain`
doit être **vide** à la fin (tout est committé).

## Étape 4 — (optionnel, pour le feeling)

Valide que ta topo corrigerait un vrai déploiement :
`containerlab deploy --dry-run -t /root/lab/topo.yaml` n'est PAS disponible
dans le labo (pas de docker imbriqué) — le linter tient lieu de CI.

Puis **Vérifier** : 10 pts = lint 5, commit « fix » 2, lien `r3:eth2` 1,
`r9` disparu 1, arbre propre 1.
