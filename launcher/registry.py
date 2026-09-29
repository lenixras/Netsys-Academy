"""Decouvre les modules du curriculum (curriculum/M*/module.yaml)."""
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = ROOT / "curriculum"


@dataclass
class Lab:
    mode: str  # topology | drills
    dir: str = "lab"
    topo: str | None = None
    checks: str | None = None
    problems: str | None = None
    ttl_min: int = 45
    setup: list = field(default_factory=list)  # [{node, cmd}] exécutés via docker exec après deploy

    def path(self, module_dir: Path) -> Path:
        return module_dir / self.dir


@dataclass
class Module:
    id: str
    title: str
    wave: int
    prereqs: list = field(default_factory=list)
    status: str = "skeleton"
    lab: Lab | None = None
    validation: dict = field(default_factory=dict)
    dir: Path | None = None

    @property
    def playable(self) -> bool:
        return self.status == "full" and self.lab is not None


def load_modules(curriculum: Path = CURRICULUM) -> dict[str, Module]:
    mods = {}
    for d in sorted(curriculum.iterdir()):
        mf = d / "module.yaml"
        if not mf.is_file():
            continue
        data = yaml.safe_load(mf.read_text())
        lab = None
        if data.get("lab"):
            lab = Lab(**data["lab"])
        m = Module(
            id=data["id"], title=data["title"], wave=data.get("wave", 0),
            prereqs=data.get("prereqs") or [], status=data.get("status", "skeleton"),
            lab=lab, validation=data.get("validation") or {}, dir=d,
        )
        mods[m.id] = m
    return mods


def main() -> int:
    mods = load_modules()
    full = [m for m in mods.values() if m.status == "full"]
    print(f"{len(mods)} modules, {len(full)} with labs: {', '.join(m.id for m in full)}")
    for m in mods.values():
        if m.playable and not (m.dir / m.lab.dir).is_dir():
            print(f"ERREUR: {m.id} lab manquant: {m.dir / m.lab.dir}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
