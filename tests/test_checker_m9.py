import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LAB = ROOT / "curriculum" / "M9-wifi" / "lab"
PROBLEMS = LAB / "problems.yaml"

# import explicite sous un nom unique : évite la collision avec le check.py de M8 (aussi "check")
_spec = importlib.util.spec_from_file_location("check_m9", LAB / "check.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def test_problemes_statiques_identiques_pour_tous():
    a = check.problems_for("alice", PROBLEMS)
    b = check.problems_for("karim", PROBLEMS)
    assert len(a) == 12
    assert [x["id"] for x in a] == [x["id"] for x in b]
    assert [x["prompt"] for x in a] == [x["prompt"] for x in b]


def test_render_retire_answer_et_accepts():
    p = check.problems_for("alice", PROBLEMS)[0]
    r = check.render(p)
    assert set(r) == {"id", "prompt"}
    assert "answer" not in r and "accepts" not in r


def test_score_bornes():
    probs = check.problems_for("bob", PROBLEMS)
    assert check.score("bob", {}, PROBLEMS)["score"] == 0
    good = {p["id"]: p["answer"] for p in probs}
    res = check.score("bob", good, PROBLEMS)
    assert res["score"] == res["max"] == 12
    bad = {p["id"]: "zzz" for p in probs}
    assert check.score("bob", bad, PROBLEMS)["score"] < 12


def test_normalisation_et_accepts():
    good = {"snr2": "  -89 ", "wpa3": "SAE", "roam": "802.11r", "pmf": "11w",
            "vlanwifi": "10.17.100.127"}
    res = check.score("carole", good, PROBLEMS)
    got = {c["id"]: c["ok"] for c in res["checks"]}
    assert all(got[i] for i in good)
