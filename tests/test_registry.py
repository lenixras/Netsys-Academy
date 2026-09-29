import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from launcher.registry import load_modules  # noqa: E402


def test_27_modules_all_playable():
    mods = load_modules()
    assert len(mods) == 27
    assert {m.id for m in mods.values() if m.playable} == {f"M{i}" for i in range(27)}


def test_playable_labs_have_files():
    for m in load_modules().values():
        if not m.playable:
            continue
        labdir = m.dir / m.lab.dir
        assert (labdir / "scenario.md").is_file(), m.id
        assert (labdir / m.lab.checks).is_file(), m.id
        if m.lab.mode == "topology":
            assert (labdir / m.lab.topo).is_file(), m.id
