"""Exécution des checks d'un lab (checks.yaml) contre une session containerlab vivante.

Contrat : chaque check = {id, node, cmd, expect (regex optionnel), points}.
La commande est exécutée DANS le conteneur du nœud (docker exec) ; exit!=0 -> échec ;
si expect, re.search(expect, stdout) doit réussir. Idempotent par construction (lecture seule).
"""
import json
import re
import sys
import time
from pathlib import Path

import yaml


def node_container(labname: str, node: str) -> str:
    return f"clab-{labname}-{node}"


def exec_node(client, labname: str, node: str, cmd: str, timeout: int = 30):
    cname = node_container(labname, node)
    try:
        c = client.containers.get(cname)
    except Exception:
        return 127, f"conteneur introuvable: {cname}"
    try:
        res = c.exec_run(["sh", "-c", cmd], demux=False)
        out = res.output.decode("utf-8", "replace") if res.output else ""
        return res.exit_code, out
    except Exception as e:  # noqa: BLE001
        return 126, str(e)


def evaluate(mod, labname: str, user: str, client=None) -> dict:
    """Score d'un lab mode topology. mod = registry.Module, labname = nom containerlab."""
    if client is None:
        import docker
        client = docker.from_env()
    checks_file = mod.dir / mod.lab.dir / mod.lab.checks
    spec = yaml.safe_load(checks_file.read_text())
    results, score, max_score = [], 0, 0
    for chk in spec["checks"]:
        pts = int(chk.get("points", 1))
        max_score += pts
        rc, out = exec_node(client, labname, chk["node"], chk["cmd"])
        ok = rc == 0
        detail = out.strip()[:400]
        if ok and chk.get("expect"):
            m = re.search(chk["expect"], out, re.M)
            ok = bool(m)
            detail = (m.group(0) if m else f"regex '{chk['expect']}' absente dans: {out[:200]}")
        if ok:
            score += pts
        results.append({"id": chk["id"], "ok": ok, "points": pts if ok else 0,
                        "detail": detail, "hint": "" if ok else chk.get("hint", "")})
    return {"lab": mod.id, "user": user, "score": score, "max": max_score, "checks": results}


def evaluate_drills(mod, user: str, answers: dict) -> dict:
    """Score d'un lab mode drills : délègue au check.py du module (importé depuis sa définition)."""
    import importlib.util
    labdir = mod.dir / mod.lab.dir
    check_py = labdir / (mod.lab.checks or "check.py")
    sys.path.insert(0, str(labdir))  # pour les imports internes du module
    try:
        spec = importlib.util.spec_from_file_location(f"labcheck_{mod.id}", check_py)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.score(user, answers, problems_path=labdir / mod.lab.problems)
    finally:
        sys.path.pop(0)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Checker autonome (labs topology)")
    p.add_argument("lab")
    p.add_argument("user")
    p.add_argument("--name", help="nom containerlab (défaut: session-<user>-<lab>)")
    p.add_argument("--out", help="écrire le JSON dans ce fichier")
    a = p.parse_args()
    from .registry import load_modules
    mods = load_modules()
    mod = mods[a.lab]
    labname = a.name or f"session-{a.user}-{mod.id.lower()}"
    result = evaluate(mod, labname, a.user)
    js = json.dumps(result, indent=2, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(js)
    print(js)
    return 0


if __name__ == "__main__":
    sys.exit(main())
