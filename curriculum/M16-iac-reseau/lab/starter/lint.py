#!/usr/bin/env python3
"""Lint des topologies containerlab du labo M16 (stdlib + PyYAML).

Verifie : name present, chaque noeud a une image, chaque endpoint designe un
noeud existant, les deux bouts d'un lien sont differents, pas de liens doubles.
Sort 0 si tout est propre, 1 sinon (erreurs affichees sur stdout).
"""

import sys

import yaml


def check(path):
    try:
        with open(path) as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        return [f"YAML invalide: {exc}"]
    if not isinstance(data, dict):
        return ["racine YAML invalide (dictionnaire attendu)"]
    errors = []
    if not data.get("name"):
        errors.append("champ name manquant en racine")
    topo = data.get("topology") or {}
    nodes = topo.get("nodes") or {}
    if not nodes:
        errors.append("aucun noeud defini dans topology.nodes")
    for name, spec in nodes.items():
        if not isinstance(spec, dict) or not spec.get("image"):
            errors.append(f"noeud {name}: image manquante")
    links = topo.get("links") or []
    seen = set()
    for i, link in enumerate(links):
        eps = (link or {}).get("endpoints") or []
        if len(eps) != 2:
            errors.append(f"lien {i}: exactement 2 endpoints attendus")
            continue
        a, b = str(eps[0]), str(eps[1])
        for ep in (a, b):
            node = ep.split(":")[0]
            if node not in nodes:
                errors.append(f"lien {i}: noeud inconnu {node} (endpoint {ep})")
        if a == b:
            errors.append(f"lien {i}: les deux bouts sont identiques ({a})")
        key = tuple(sorted((a, b)))
        if key in seen:
            errors.append(f"lien {i}: lien en double ({a} <-> {b})")
        seen.add(key)
    return errors


def main():
    if len(sys.argv) != 2:
        print("usage: lint.py <chemin/topo.yaml>")
        return 2
    errors = check(sys.argv[1])
    for err in errors:
        print("ERREUR:", err)
    if errors:
        print(f"lint: {len(errors)} erreur(s)")
        return 1
    print("lint: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
