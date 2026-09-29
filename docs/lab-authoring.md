# Créer un labo (auteur)

Un module = un dossier `curriculum/Mx-slug/` :

```
M9-wifi/
├── module.yaml      # id, title, wave, prereqs, status: full, lab: {…}
├── theory.md        # contenu du cours
├── quiz.yaml        # questions (à importer dans la banque Moodle)
└── lab/
    ├── topology.yaml    # containerlab (mode: topology) — ou rien si mode: drills
    ├── scenario.md      # consignes pas-à-pas ( Killercoda-like )
    └── checks.yaml      # critères machine
```

## `module.yaml`

```yaml
status: full
lab:
  mode: topology        # ou drills (sans conteneur)
  dir: lab
  topo: topology.yaml   # mode topology
  checks: checks.yaml
  ttl_min: 45
```

## Nœuds

- `kind: linux` + image `netsys/labnode:2` (build `--build-arg FULL=1` : iproute2,
  bridge, iperf3, tcpdump/tshark, jq, bind9, dnsmasq, chrony, snmp, openssh, sudo,
  ansible-core, pytest, nftables, git) pour hôtes, switches (bridges) et boîtes nftables.
- `kind: frr` + image `frrouting/frr:latest` pour les routeurs (vtysh dispo).
- Toujours partir d'une config **vide** : c'est l'élève qui configure ; le premier
  `verify` doit donner un score < max (test d'échec avant, obligatoire).

## `checks.yaml`

```yaml
checks:
- id: ping_h1_h2          # unique, sert au reporting
  node: h1                # conteneur où la commande tourne (docker exec)
  cmd: ping -c2 -W1 10.10.20.10
  expect: "0% packet loss"  # regex re.MULTILINE sur stdout+stderr ; absent => exit 0
  points: 2               # poids pédagogique
  hint: "verifier que le port est bien trunk (bridge vlan show)"  # affiché à l'élève si FAIL
```

Règles :
1. **Idempotent** : lecture seule uniquement (`show`, `cat /sys/...`, pings) — jamais de
   mutation dans un check.
2. **Vue nœud** : privilégier les commandes que l'élève taperait (`vtysh -c "show ip ospf
   neighbor"`, `bridge vlan show`) ; les pings inter-nœuds valident le réseau réel.
3. Un check par compétence listée dans les critères de validation du module.
4. Total des points = `max` du score.
5. **Un `hint` par check** : 1-2 phrases actionnables (quelle commande, quel nœud),
   sans donner la réponse exacte.

## `quiz.yaml`

```yaml
questions:
- q: "Que fait un port trunk ?"
  choices: ["…", "…", "…", "…"]
  answer: 0               # index du choix correct
  points: 1
  expl: "Un trunk transporte plusieurs VLANs via des tags 802.1Q."  # vue après correction
```

Le launcher sert le quiz via `/api/quiz/{lab}` : `answer`/`expl` ne partent jamais
avant la correction ; le score est persisté comme les labs (suffixe `-quiz`).

## Valider un lab avant de le publier

```bash
containerlab deploy -t curriculum/Mx-…/lab/topology.yaml --name manuel-mx
# faire le scenario à la main…
uv run python -m launcher.checker Mx tester --name manuel-mx   # doit passer
containerlab destroy --name manuel-mx
containerlab deploy -t …/topology.yaml --name manuel-mx        # state neuf
uv run python -m launcher.checker Mx tester --name manuel-mx   # doit ÊTRE < max
```

Mode `drills` : fournir `lab/problems.yaml` (types + compte) et `lab/check.py` exposant
`problems_for(user, problems_path, lab)`, `render(p)`, `score(user, answers, problems_path, lab)`
(voir M8 comme référence).
