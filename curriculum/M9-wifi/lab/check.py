"""Correcteur M9 — drills « plan d'implantation Wi-Fi », 100 % stdlib (hors yaml du projet).

Contrairement à M8, les problèmes sont STATIQUES (liste `problems:` dans problems.yaml) :
tout le monde voit les 12 mêmes exercices, le tirage est donc identique pour tous.
API identique à M8 : problems_for / render / score. Idempotent.
"""
import json
import sys
from pathlib import Path

import yaml


def _norm(v: str) -> str:
    return str(v).strip().lower().replace(" ", "")


def _all(problems_path: Path) -> list[dict]:
    spec = yaml.safe_load(Path(problems_path).read_text())
    return list(spec["problems"])


def render(p: dict) -> dict:
    return {"id": p["id"], "prompt": p["prompt"]}


def problems_for(user: str, problems_path: Path, lab: str = "M9") -> list[dict]:
    # Pas de tirage : les 12 exercices sont les mêmes pour tous les users.
    return _all(problems_path)


def score(user: str, answers: dict, problems_path: Path, lab: str = "M9", seed: int | None = None) -> dict:
    checks, got = [], 0
    for p in _all(problems_path):
        admises = [_norm(p["answer"])] + [_norm(a) for a in p.get("accepts", [])]
        ok = _norm(str(answers.get(p["id"], ""))) in admises
        got += ok
        checks.append({"id": p["id"], "ok": ok, "points": 1,
                       "detail": p["answer"] if not ok else "OK"})
    return {"lab": lab, "user": user, "score": got, "max": len(checks), "checks": checks}


if __name__ == "__main__":
    u = sys.argv[1]
    answers = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {}
    pp = Path(__file__).parent / "problems.yaml"
    for q in problems_for(u, pp):
        print(f"[{q['id']}] {q['prompt']}")
    if answers:
        print(json.dumps(score(u, answers, pp), indent=2))
