# M16 — spec du plan reseau `m16-design`

Le fichier `/root/lab/topo.yaml` livre est **casse** (3 erreurs detectees par
`python3 /root/lab/lint.py /root/lab/topo.yaml`). Le tableau ci-dessous est le
plan FINAL a retablir : 4 noeuds avec image, 4 liens, aucune reference a `r9`.

## Noeuds (tous `kind: linux`, `image: netsys/labnode:2`)

| Noeud | Role |
|---|---|
| r1  | routeur nord |
| r2  | routeur centre |
| r3  | routeur sud |
| sw1 | switch d'acces |

## Liens (plan d'adressage des interfaces)

| # | Endpoint A | Endpoint B |
|---|---|---|
| 1 | r1:eth1 | r2:eth1 |
| 2 | r2:eth2 | r3:eth1 |
| 3 | r1:eth2 | sw1:eth1 |
| 4 | r3:eth2 | sw1:eth2 |

## YAML attendu en fin de labo (identique, indentation 2 espaces)

```yaml
name: m16-design
topology:
  nodes:
    r1:
      kind: linux
      image: netsys/labnode:2
    r2:
      kind: linux
      image: netsys/labnode:2
    r3:
      kind: linux
      image: netsys/labnode:2
    sw1:
      kind: linux
      image: netsys/labnode:2
  links:
    - endpoints: ["r1:eth1", "r2:eth1"]
    - endpoints: ["r2:eth2", "r3:eth1"]
    - endpoints: ["r1:eth2", "sw1:eth1"]
    - endpoints: ["r3:eth2", "sw1:eth2"]
```

## Procedure

1. Edite `/root/lab/topo.yaml` avec l'editeur integre (nœud `dev2`).
2. `python3 /root/lab/lint.py /root/lab/topo.yaml` doit afficher `lint: OK` (exit 0).
3. Commite : `git -C /root/lab add -A && git -C /root/lab commit -m "fix topo"`
   (l'identite git est deja configuree dans le depot).
