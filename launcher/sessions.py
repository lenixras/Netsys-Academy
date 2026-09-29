"""Sessions de lab : registre SQLite, TTL, sweeper, purge des orphelins containerlab."""
import asyncio
import contextlib
import os
import sqlite3
import time
import uuid
from pathlib import Path

from .runner import destroy as clab_destroy, orphan_session_names

DB = Path(__file__).resolve().parent.parent / "var" / "sessions.sqlite3"
MAX_CONCURRENT = int(os.environ.get("NETSYS_MAX_SESSIONS", "2"))


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE IF NOT EXISTS sessions(
             id TEXT PRIMARY KEY, auth_provider TEXT DEFAULT 'local',
             user TEXT NOT NULL, lab TEXT NOT NULL, clab_name TEXT NOT NULL,
             state TEXT NOT NULL, created REAL, last_active REAL, ttl_min INT)"""
    )
    return c


def create(user: str, lab: str, clab_name: str, ttl_min: int) -> dict:
    with _conn() as c:
        n = c.execute("SELECT count(*) FROM sessions WHERE state='running'").fetchone()[0]
        if n >= MAX_CONCURRENT:
            raise RuntimeError(f"{MAX_CONCURRENT} sessions déjà en cours — essaye plus tard")
        sid = uuid.uuid4().hex[:8]
        now = time.time()
        c.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
            (sid, "local", user, lab, clab_name, "running", now, now, ttl_min),
        )
    return get(sid)


def get(sid: str) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    return dict(r) if r else None


def get_running(user: str, lab: str) -> dict | None:
    with _conn() as c:
        r = c.execute(
            "SELECT * FROM sessions WHERE user=? AND lab=? AND state='running'", (user, lab)
        ).fetchone()
    return dict(r) if r else None


def touch(sid: str) -> None:
    with _conn() as c:
        c.execute("UPDATE sessions SET last_active=? WHERE id=?", (time.time(), sid))


def mark_destroyed(sid: str) -> None:
    with _conn() as c:
        c.execute("UPDATE sessions SET state='destroyed' WHERE id=?", (sid,))


def destroy(sid: str) -> dict:
    s = get(sid)
    if not s:
        raise KeyError(sid)
    if s["clab_name"]:
        clab_destroy(s["clab_name"])
    mark_destroyed(sid)
    return s


def running() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM sessions WHERE state='running'")]


def _destroy(s: dict) -> None:
    with contextlib.suppress(Exception):
        clab_destroy(s["clab_name"])
    with _conn() as c:
        c.execute("UPDATE sessions SET state='destroyed' WHERE id=?", (s["id"],))


async def sweeper(period: float = 60.0) -> None:
    """Détruit les sessions dont le TTL est écoulé (inactivité)."""
    while True:
        now = time.time()
        for s in running():
            if now - s["last_active"] > s["ttl_min"] * 60:
                _destroy(s)
        await asyncio.sleep(period)


def gc_orphans() -> list[str]:
    """Détruit tout lab containerlab 'session-*' sans ligne running en base (crash, redémarrage)."""
    known = {s["clab_name"] for s in running()}
    removed = []
    for name in orphan_session_names(known):
        clab_destroy(name)
        removed.append(name)
    return removed


if __name__ == "__main__":
    import sys
    if "--gc" in sys.argv:
        print("purgé:", gc_orphans())
    else:
        for s in running():
            print(s)
