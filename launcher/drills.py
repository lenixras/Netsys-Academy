"""Labs 'drills' (sans conteneur) : le module fournit son check.py (render/problems_for/score)."""
import importlib.util
import sys
from pathlib import Path


def _lab_check(mod):
    labdir = mod.dir / mod.lab.dir
    check_py = labdir / (mod.lab.checks or "check.py")
    spec = importlib.util.spec_from_file_location(f"labcheck_{mod.id}", check_py)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(labdir))
    try:
        spec.loader.exec_module(m)
    finally:
        sys.path.pop(0)
    return m


def load_problems(mod, user: str) -> list[dict]:
    """Tirage déterministe par user (mêmes questions pour les vérifs successives)."""
    checker = _lab_check(mod)
    probs = checker.problems_for(user, mod.dir / mod.lab.dir / mod.lab.problems, lab=mod.id)
    return [checker.render(p) for p in probs]


def score_drills(mod, user: str, answers: dict) -> dict:
    checker = _lab_check(mod)
    return checker.score(user, answers, mod.dir / mod.lab.dir / mod.lab.problems, lab=mod.id)
