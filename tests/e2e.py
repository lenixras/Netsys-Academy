"""E2E réel (nécessite containerlab + docker + hôte préparé) :
  login -> launch -> check vide < max -> solve -> check == max -> destroy.
Usage: uv run python tests/e2e.py [M5 M6 M7 M8]"""
import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import launcher.app as A  # noqa: E402
from launcher import sessions  # noqa: E402
from launcher.checker import exec_node  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def solve(client, labname: str, lab: str, wait_s: int = 5):
    cmds = json.loads((ROOT / "tests" / f"solve_{lab}.json").read_text())
    for node, lines in cmds.items():
        for line in lines:
            rc, out = exec_node(A.DOCKER, labname, node, line)
            assert rc == 0, f"{node}: {line!r} -> rc={rc} {out[:200]}"
    time.sleep(wait_s)


def run(c: TestClient, c2: TestClient, lab: str):
    s = c.post("/api/session/launch", json={"lab": lab})
    assert s.status_code == 200, s.text
    sess = s.json()["session"]
    try:
        if A.MODULES[lab].lab.mode == "drills":
            v = c.post("/api/session/verify", json={"sid": sess["id"], "answers": {}}).json()
            assert v["score"] < v["max"], v
            print(f"{lab}: vide {v['score']}/{v['max']}")
            mod = A.MODULES[lab]
            from launcher.drills import _lab_check
            probs = _lab_check(mod).problems_for("e2euser", mod.dir / mod.lab.dir / mod.lab.problems, lab=lab)
            v = c.post("/api/session/verify", json={"sid": sess["id"],
                       "answers": {p["id"]: p["answer"] for p in probs}}).json()
            assert v["score"] == v["max"], v
            print(f"{lab}: configuré {v['score']}/{v['max']}")
            return
        v = c.post("/api/session/verify", json={"sid": sess["id"]}).json()
        assert v["score"] < v["max"], f"checks passent sans config: {v}"
        print(f"{lab}: vide {v['score']}/{v['max']}")
        solve(c, sess["clab_name"], lab, wait_s=60 if lab == "M5" else 15)
        # convergence réseau bornée : on re-vérifie jusqu'à ce que tout passe (max 90 s)
        for _ in range(18):
            v = c.post("/api/session/verify", json={"sid": sess["id"]}).json()
            fails = [x for x in v["checks"] if not x["ok"]]
            if not fails:
                break
            time.sleep(5)
        print(f"{lab}: configuré {v['score']}/{v['max']}", "" if not fails else f"FAILS: {fails}")
        assert not fails
    finally:
        c.post("/api/session/destroy", json={"sid": sess["id"]})
    # isolation: un autre user ne voit pas la session détruite / relance ok
    c2.post("/api/session/destroy", json={"sid": sess["id"]})


if __name__ == "__main__":
    labs = sys.argv[1:] or ["M5", "M6", "M7", "M8"]
    c = TestClient(A.app)
    c.post("/login", data={"user": "e2euser"})
    c2 = TestClient(A.app)
    c2.post("/login", data={"user": "autre"})
    t0 = time.time()
    for lab in labs:
        before = sessions.running()
        run(c, c2, lab)
        assert len(sessions.running()) <= len(before)
    print(f"E2E OK en {time.time() - t0:.0f}s ; sessions restantes: {sessions.running()}")
