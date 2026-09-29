"""Tests sessions (SQLite) sans containerlab."""
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from launcher import sessions


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DB", tmp_path / "s.sqlite3")
    monkeypatch.setattr(sessions, "clab_destroy", lambda name: None)


def test_create_max_concurrent():
    sessions.create("alice", "M5", "session-alice-m5", 45)
    sessions.create("bob", "M6", "session-bob-m6", 45)
    with pytest.raises(RuntimeError):
        sessions.create("carole", "M7", "session-carole-m7", 45)


def test_touch_et_ttl():
    s = sessions.create("alice", "M5", "session-alice-m5", 45)
    with sessions._conn() as c:
        c.execute("UPDATE sessions SET last_active=? WHERE id=?", (time.time() - 3600, s["id"]))
    # le sweeper détruit après TTL : on vérifie la sélection manuellement
    stale = [x for x in sessions.running() if time.time() - x["last_active"] > x["ttl_min"] * 60]
    assert [x["id"] for x in stale] == [s["id"]]
    sessions.destroy(s["id"])
    assert sessions.running() == []


def test_orphans_gc(tmp_path, monkeypatch):
    destroyed = []
    monkeypatch.setattr(sessions, "clab_destroy", destroyed.append)
    monkeypatch.setattr(sessions, "orphan_session_names",
                        lambda known: [n for n in ["session-x-m5", "session-alice-m6", "prod-lab"]
                                       if n.startswith("session-") and n not in known])
    s = sessions.create("alice", "M6", "session-alice-m6", 45)
    assert sessions.gc_orphans() == ["session-x-m5"]
    assert destroyed == ["session-x-m5"]
