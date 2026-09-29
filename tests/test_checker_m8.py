import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
LAB = Path(__file__).resolve().parent.parent / "curriculum" / "M8-subnetting" / "lab"
sys.path.insert(0, str(LAB))

import check  # noqa: E402

PROBLEMS = LAB / "problems.yaml"


def test_deterministe_par_user():
    a = check.problems_for("alice", PROBLEMS)
    b = check.problems_for("alice", PROBLEMS)
    assert [x["id"] for x in a] == [x["id"] for x in b]
    assert [x["prompt"] for x in a] == [x["prompt"] for x in b]
    assert len(a) == 12


def test_score_bornes():
    probs = check.problems_for("bob", PROBLEMS)
    assert check.score("bob", {}, PROBLEMS)["score"] == 0
    good = {p["id"]: p["answer"] for p in probs}
    assert check.score("bob", good, PROBLEMS)["score"] == 12


def test_normalisation_ipv6_et_espaces():
    probs = check.problems_for("carole", PROBLEMS)
    v6 = next(p for p in probs if p["type"] == "ipv6")
    padded = f"  {v6['answer'].replace('::', ':0:0:0:0:0:0:0:0:').replace('2001:db8', '2001:0db8')}  "
    # l'entrée 'pleine' doit être reconnue via ipaddress
    import ipaddress
    full = str(ipaddress.ip_address(v6["answer"]))
    assert check.score("carole", {v6["id"]: full}, PROBLEMS)["checks"][
        next(i for i, p in enumerate(probs) if p["id"] == v6["id"])]["ok"]
