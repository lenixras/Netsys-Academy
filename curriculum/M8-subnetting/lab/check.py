"""Correcteur M8 — drills de subnetting 100 % stdlib (ipaddress). Idempotent."""
import hashlib
import ipaddress
import itertools
import json
import random
import sys
from pathlib import Path

import yaml

PROMPTS = {
    "network": "Adresse réseau de {a} (ex: 10.0.4.128)",
    "broadcast": "Adresse de broadcast du réseau {a}",
    "hosts": "Nombre d'adresses d'hôtes utilisables dans {a} (nombre seul)",
    "prefix": "Plus petit préfixe IPv4 accueillant {n} hôtes (répondre la longueur, ex: 27)",
    "ipv6": "Adresse réseau du sous-réseau /64 n°{n} (0-indexé) du préfixe {a}",
}


def _norm(v: str) -> str:
    v = v.strip().lower()
    try:
        return str(ipaddress.ip_address(v.split("/")[0]))
    except ValueError:
        return v


def _gen(rng: random.Random, types: dict, count: int) -> list[dict]:
    problems = []
    for t, n in types.items():
        for _ in range(n):
            o4 = rng.randint
            if t == "network":
                pfx = rng.randint(16, 30)
                net = ipaddress.ip_network(f"10.{o4(0, 255)}.{o4(0, 255)}.0/{pfx}", strict=False)
                a = f"{net[rng.randint(1, net.num_addresses - 2)]}/{pfx}"
                prompt, ans = PROMPTS[t].format(a=a), str(net.network_address)
            elif t == "broadcast":
                net = ipaddress.ip_network(f"172.{o4(0, 255)}.{o4(0, 255)}.0/{rng.randint(16, 30)}", strict=False)
                prompt, ans = PROMPTS[t].format(a=str(net)), str(net.broadcast_address)
            elif t == "hosts":
                pfx = rng.randint(8, 30)
                prompt, ans = PROMPTS[t].format(a=f"192.168.{o4(0, 255)}.0/{pfx}"), str(2 ** (32 - pfx) - 2)
            elif t == "prefix":
                n_hosts = rng.choice([2, 6, 14, 30, 62, 126, 254, 500, 1000, 4000])
                p = 31
                while 2 ** (32 - p) - 2 < n_hosts:
                    p -= 1
                prompt, ans = PROMPTS[t].format(n=n_hosts), str(p)
            elif t == "ipv6":
                idx = rng.randint(1, 40)
                site = f"2001:db8:{rng.choice('abcd')}{o4(10, 99)}::/48"
                net6 = ipaddress.ip_network(site)
                sub = next(itertools.islice(net6.subnets(new_prefix=64), idx, idx + 1))
                prompt, ans = PROMPTS[t].format(a=site, n=idx), str(sub.network_address)
            else:
                continue
            problems.append({"id": f"{t}-{len(problems)}", "type": t, "prompt": prompt, "answer": ans})
    return problems[:count]


def _seed_for(user: str, lab: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{user}:{lab}".encode()).digest()[:4], "big")


def _all(seed: int, problems_path: Path) -> list[dict]:
    spec = yaml.safe_load(Path(problems_path).read_text())
    return _gen(random.Random(seed), spec["types"], spec.get("count", 12))


def render(p: dict) -> dict:
    return {"id": p["id"], "prompt": p["prompt"]}


def problems_for(user: str, problems_path: Path, lab: str = "M8") -> list[dict]:
    return _all(_seed_for(user, lab), problems_path)


def score(user: str, answers: dict, problems_path: Path, lab: str = "M8", seed: int | None = None) -> dict:
    rng_seed = seed if seed is not None else _seed_for(user, lab)
    checks, got = [], 0
    for p in _all(rng_seed, problems_path):
        ok = _norm(str(answers.get(p["id"], ""))) == _norm(p["answer"])
        got += ok
        checks.append({"id": p["id"], "ok": ok, "points": 1,
                       "detail": p["answer"] if not ok else "OK"})
    return {"lab": lab, "user": user, "score": got, "max": len(checks), "checks": checks}


if __name__ == "__main__":
    u = sys.argv[1]
    answers = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {}
    for q in problems_for(u, Path(__file__).parent / "problems.yaml"):
        print(f"[{q['id']}] {q['prompt']}")
    if answers:
        print(json.dumps(score(u, answers, Path(__file__).parent / "problems.yaml"), indent=2))
