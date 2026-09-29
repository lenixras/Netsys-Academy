"""Poussée de note : Moodle REST si configuré, sinon JSON local dans var/scores/."""
import json
import os
import time
from pathlib import Path

SCORES = Path(__file__).resolve().parent.parent / "var" / "scores"


def _moodle_cfg() -> dict | None:
    url, tok, course = (os.environ.get(k) for k in ("MOODLE_URL", "MOODLE_TOKEN", "MOODLE_COURSE_ID"))
    if url and tok and course:
        return {"url": url.rstrip("/"), "token": tok, "course": int(course)}
    return None


def push(score: dict) -> dict:
    """Renvoie {'pushed': 'moodle'|'local', ...}."""
    SCORES.mkdir(parents=True, exist_ok=True)
    fname = SCORES / f"{time.strftime('%Y%m%d-%H%M%S')}-{score['user']}-{score['lab']}.json"
    fname.write_text(json.dumps(score, ensure_ascii=False, indent=2))
    cfg = _moodle_cfg()
    if not cfg:
        return {"pushed": "local", "file": str(fname)}
    try:
        import httpx
        base = f"{cfg['url']}/webservice/rest/server.php"
        uid = httpx.post(base, params={"moodlewsrestformat": "json"}, data={
            "wsfunction": "core_users_get_users_by_field", "wstoken": cfg["token"],
            "field": "username", "values[0]": score["user"],
        }, timeout=15).json()
        if not isinstance(uid, list) or not uid:
            raise RuntimeError(f"utilisateur Moodle '{score['user']}' inconnu")
        res = httpx.post(base, params={"moodlewsrestformat": "json"}, data={
            "wsfunction": "core_grades_update_grades", "wstoken": cfg["token"],
            "courseid": cfg["course"], "itemid": 0,
            "grades[0][userid]": uid[0]["id"],
            "grades[0][itemname]": f"TP {score['lab']}",
            "grades[0][rawgrade]": score["score"],
        }, timeout=15).json()
        if isinstance(res, dict) and res.get("exception"):
            raise RuntimeError(res.get("message", "erreur Moodle"))
        return {"pushed": "moodle", "file": str(fname), "moodle_userid": uid[0]["id"]}
    except Exception as e:  # noqa: BLE001
        return {"pushed": "local", "file": str(fname), "moodle_error": str(e)}
