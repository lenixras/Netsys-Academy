"""Lanceur web des labs : login pseudo, sessions containerlab, terminal WS, vérification."""
import asyncio
import base64
import contextlib
import json
import os
import re
import secrets
from pathlib import Path

import docker
import markdown as md
import yaml
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import checker, sessions, terminal
from .registry import Module, load_modules

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="netsys-academy launcher")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")
DOCKER = docker.from_env()
MODULES: dict[str, Module] = load_modules()
SECRET = os.environ.get("NETSYS_SECRET")
if not SECRET:  # survit aux redémarrages, sinon les cookies expirent à chaque boot
    f = ROOT / "var" / "netsys.secret"
    SECRET = f.read_text().strip() if f.is_file() else secrets.token_hex(16)
    f.write_text(SECRET)


def _serializer():
    from itsdangerous import URLSafeSerializer
    return URLSafeSerializer(SECRET)


# --- auth locale : cookie signé (point d'extension SSO/LTI — cf docs/architecture.md)
@app.middleware("http")
async def sign_in(request: Request, call_next):
    from itsdangerous import BadSignature
    cookie = request.cookies.get("netsys_user")
    request.state.user = None
    if cookie:
        with contextlib.suppress(BadSignature):
            request.state.user = _serializer().loads(cookie)
    resp = await call_next(request)
    if request.url.path.startswith("/static/"):  # sinon le navigateur garde l'ancien app.js en cache
        resp.headers["cache-control"] = "no-cache"
    return resp


def user_of(request: Request) -> str:
    if not getattr(request.state, "user", None):
        raise HTTPException(401, "non connecté")
    return request.state.user


def _sign(value: str) -> str:
    return _serializer().dumps(value)


def topo_nodes(mod: Module) -> list[str]:
    topo = yaml.safe_load((mod.dir / mod.lab.dir / mod.lab.topo).read_text())
    return list(topo["topology"]["nodes"])


def _deployed_topo(s, mod):
    """Topo réellement déployée (issue de la copie de session si édition récente)."""
    if s and s["clab_name"]:
        f = ROOT / "var" / "labs" / s["clab_name"] / "topology.yaml"
        if f.is_file():
            return yaml.safe_load(f.read_text())
    return yaml.safe_load((mod.dir / mod.lab.dir / mod.lab.topo).read_text())


def _lab_or_404(lab_id: str) -> Module:
    mod = MODULES.get(lab_id)
    if not mod or not mod.playable:
        raise HTTPException(404, f"lab {lab_id} indisponible")
    return mod


def _waves(mods):
    return [(w, [m for m in mods if m.wave == w]) for w in sorted({m.wave for m in mods})]


# --- pages
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    mods = sorted(MODULES.values(), key=lambda m: m.id)
    return templates.TemplateResponse(request, "index.html",
                                      {"waves": _waves(mods), "user": getattr(request.state, "user", None)})


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    user = str(form.get("user", "")).strip().lower()
    if not (2 <= len(user) <= 32 and user.replace("-", "").replace("_", "").isalnum()):
        raise HTTPException(400, "pseudo : 2-32 caractères alphanumériques")
    mods = sorted(MODULES.values(), key=lambda m: m.id)
    resp = templates.TemplateResponse(request, "index.html",
                                      {"waves": _waves(mods), "user": user}, status_code=200)
    resp.set_cookie("netsys_user", _sign(user))
    return resp


@app.get("/lab/{lab_id}", response_class=HTMLResponse)
def lab_page(request: Request, lab_id: str):
    user = user_of(request)
    mod = _lab_or_404(lab_id)
    scenario = ""
    sf = mod.dir / mod.lab.dir / "scenario.md"
    if sf.is_file():
        scenario = md.markdown(sf.read_text(), extensions=["fenced_code", "tables"])
    theory = ""
    tf = mod.dir / "theory.md"
    if tf.is_file():
        theory = md.markdown(tf.read_text(), extensions=["fenced_code", "tables"])
    quiz_n = len(yaml.safe_load((mod.dir / "quiz.yaml").read_text())["questions"]) \
        if (mod.dir / "quiz.yaml").is_file() else 0
    problems = None
    if mod.lab.mode == "drills":
        problems = checker_drills(mod, user)
    session = sessions.get_running(user, mod.id)
    return templates.TemplateResponse(request, "lab.html", {
        "mod": mod, "user": user, "scenario": scenario, "theory": theory, "quiz_n": quiz_n,
        "problems": problems,
        "nodes": topo_nodes(mod) if mod.lab.mode == "topology" else [],
        "session": session,
    })


def checker_drills(mod: Module, user: str):
    from .drills import load_problems
    return load_problems(mod, user)


# --- API sessions
class LabBody(BaseModel):
    lab: str


class VerifyBody(BaseModel):
    sid: str
    answers: dict[str, str] | None = None


@app.post("/api/session/launch")
def api_launch(request: Request, body: LabBody):
    user = user_of(request)
    mod = _lab_or_404(body.lab)
    existing = sessions.get_running(user, mod.id)
    if existing:
        return {"session": existing, "nodes": topo_nodes(mod)}
    ttl = int(os.environ.get("NETSYS_TTL_MIN", mod.lab.ttl_min))
    if mod.lab.mode == "drills":
        sid = sessions.create(user, mod.id, "", ttl)
        return {"session": sid, "nodes": []}
    name = f"session-{user}-{mod.id.lower()}"
    topo = mod.dir / mod.lab.dir / mod.lab.topo
    try:
        from .runner import deploy
        deploy(str(topo), name)
        for st in mod.lab.setup or []:
            rc, out = checker.exec_node(DOCKER, name, st["node"], st["cmd"], timeout=60)
            if rc != 0:
                raise RuntimeError(f"setup {st['node']}: {out[:300]}")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"déploiement impossible: {e}") from e
    sid = sessions.create(user, mod.id, name, ttl)
    return {"session": sid, "nodes": topo_nodes(mod)}


@app.post("/api/session/destroy")
def api_destroy(request: Request, body: VerifyBody):
    user = user_of(request)
    s = sessions.get(body.sid)
    if not s or s["user"] != user:
        raise HTTPException(404, "session inconnue")
    if s["state"] == "running" and s["clab_name"]:
        try:
            sessions.destroy(body.sid)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, str(e)) from e
    else:
        with contextlib.suppress(KeyError):
            sessions.destroy(body.sid)
    return {"ok": True}


@app.post("/api/session/verify")
def api_verify(request: Request, body: VerifyBody):
    user = user_of(request)
    s = sessions.get(body.sid)
    if not s or s["user"] != user:
        raise HTTPException(404, "session inconnue")
    mod = _lab_or_404(s["lab"])
    sessions.touch(s["id"])
    if mod.lab.mode == "drills":
        from .drills import score_drills
        result = score_drills(mod, user, body.answers or {})
    else:
        if s["state"] != "running":
            raise HTTPException(409, "session expirée — relance le labo")
        result = checker.evaluate(mod, s["clab_name"], user, client=DOCKER)
    from .moodle import push
    result["push"] = push(result)
    return JSONResponse(result)


# --- topologie, éditeur de fichiers, progression
_SAFE_PATH = re.compile(r"^[\w./@-]+$")


def _session_node(user: str, sid: str, node: str):
    s = sessions.get(sid)
    if not s or s["user"] != user:
        raise HTTPException(404, "session inconnue")
    mod = _lab_or_404(s["lab"])
    if s["state"] != "running" or not s["clab_name"]:
        raise HTTPException(409, "session expirée")
    if node not in _deployed_topo(s, mod)["topology"]["nodes"]:
        raise HTTPException(400, f"nœud {node} inconnu")
    return s, mod


@app.get("/api/topo/{lab_id}")
def api_topo(request: Request, lab_id: str, sid: str | None = None):
    user = user_of(request)
    mod = _lab_or_404(lab_id)
    if mod.lab.mode != "topology":
        return {"nodes": [], "links": []}
    s = sessions.get(sid) if sid else None
    t = _deployed_topo(s if (s and s["user"] == user) else None, mod)
    topo = t["topology"]
    nodes = [{"name": n, "kind": v.get("kind", "linux"), "image": v.get("image", "")}
             for n, v in topo["nodes"].items()]
    links = []
    for l in topo.get("links") or []:
        (a, b) = l["endpoints"]
        links.append({"a": a.split(":")[0], "b": b.split(":")[0],
                      "a_if": a.split(":")[1], "b_if": b.split(":")[1]})
    return {"nodes": nodes, "links": links}


_OK_IMG = {"netsys/labnode:1", "netsys/labnode:2", "netsys/labnode:3", "netsys/frrlab:1", "netsys/frrlab:2", "frrouting/frr:latest"}
_OK_NODE = re.compile(r"^[a-z][a-z0-9_-]{0,20}$")
_MAX_NODES = int(os.environ.get("NETSYS_MAX_TOPO_NODES", "8"))  # RAM hôte


class TopoEditBody(BaseModel):
    sid: str
    nodes: list[dict]
    links: list[dict]


@app.post("/api/session/topo")
def api_topo_edit(request: Request, body: TopoEditBody):
    """Le student redessine la topo : destroy + redeploy + re-setup → machines NEUVES."""
    user = user_of(request)
    s = sessions.get(body.sid)
    if not s or s["user"] != user:
        raise HTTPException(404, "session inconnue")
    mod = _lab_or_404(s["lab"])
    if mod.lab.mode != "topology":
        raise HTTPException(400, "pas de topologie pour ce module")
    names = []
    for n in body.nodes:
        name = n.get("name", "")
        if not _OK_NODE.match(name) or name in names:
            raise HTTPException(400, f"nom de nœud invalide ou dupliqué : {name!r}")
        if n.get("kind", "linux") not in ("linux", "frr"):
            raise HTTPException(400, f"kind non autorisé : {n.get('kind')}")
        if n.get("image", "netsys/labnode:2") not in _OK_IMG:
            raise HTTPException(400, f"image non autorisée : {n.get('image')}")
        names.append(name)
    if not 1 <= len(names) <= _MAX_NODES:
        raise HTTPException(400, f"entre 1 et {_MAX_NODES} nœuds (mémoire de l'hôte)")
    links = []
    for l in body.links:
        if l.get("a") not in names or l.get("b") not in names:
            raise HTTPException(400, "lien vers un nœud inconnu")
        links.append({"endpoints": [f"{l['a']}:{l.get('a_if', 'eth1')}",
                                    f"{l['b']}:{l.get('b_if', 'eth1')}"]})
    t = _deployed_topo(s, mod)
    new = {"name": t["name"], "mgmt": t.get("mgmt", {}),
           "topology": {"nodes": {n["name"]: {"kind": n.get("kind", "linux"),
                                              "image": n.get("image", "netsys/labnode:2")}
                                  for n in body.nodes}, "links": links}}
    edit = ROOT / "var" / "labs" / f"{s['clab_name']}-edit.yaml"
    edit.write_text(yaml.safe_dump(new, sort_keys=False))
    from .runner import deploy, destroy
    try:
        destroy(s["clab_name"])
        deploy(str(edit), s["clab_name"])
        edit.unlink(missing_ok=True)
        warns = []
        for st in mod.lab.setup or []:
            if st["node"] not in names:
                warns.append(f"setup ignoré (nœud {st['node']} supprimé)")
                continue
            rc, out = checker.exec_node(DOCKER, s["clab_name"], st["node"], st["cmd"], timeout=60)
            if rc != 0:
                warns.append(f"setup {st['node']}: {out[:120]}")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"re-déploiement impossible: {e}") from e
    sessions.touch(s["id"])
    return {"ok": True, "warnings": warns, "nodes": names}


class RunBody(BaseModel):
    sid: str
    node: str
    cmd: str


@app.post("/api/run")
def api_run(request: Request, body: RunBody):
    """Une commande dans le conteneur de l'étudiant (même confiance que le terminal)."""
    user = user_of(request)
    s, _ = _session_node(user, body.sid, body.node)
    sessions.touch(s["id"])
    rc, out = checker.exec_node(DOCKER, s["clab_name"], body.node, body.cmd)
    return {"rc": rc, "out": out[:4000]}


class FileBody(BaseModel):
    sid: str
    node: str
    path: str
    content: str


@app.get("/api/file")
def api_file_read(request: Request, sid: str, node: str, path: str):
    user = user_of(request)
    s, _ = _session_node(user, sid, node)
    if not _SAFE_PATH.match(path):
        raise HTTPException(400, "chemin invalide")
    rc, out = checker.exec_node(DOCKER, s["clab_name"], node, f"base64 {path}")
    if rc != 0:
        raise HTTPException(404, out[:200])
    return {"content": base64.b64decode(out).decode("utf-8", "replace")}


@app.post("/api/file")
def api_file_write(request: Request, body: FileBody):
    user = user_of(request)
    s, _ = _session_node(user, body.sid, body.node)
    if not _SAFE_PATH.match(body.path):
        raise HTTPException(400, "chemin invalide")
    b64 = base64.b64encode(body.content.encode()).decode()
    rc, out = checker.exec_node(DOCKER, s["clab_name"], body.node,
                                f"mkdir -p $(dirname {body.path}) && echo {b64} | base64 -d > {body.path}")
    if rc != 0:
        raise HTTPException(500, out[:200])
    return {"ok": True}


# --- quiz interactifs
class QuizBody(BaseModel):
    answers: list[int]


def _quiz_questions(mod: Module):
    qf = mod.dir / "quiz.yaml"
    if not qf.is_file():
        raise HTTPException(404, "pas de quiz pour ce module")
    return yaml.safe_load(qf.read_text())["questions"]


@app.get("/api/quiz/{lab_id}")
def api_quiz_get(request: Request, lab_id: str):
    user_of(request)
    qs = _quiz_questions(_lab_or_404(lab_id))
    return {"questions": [{"q": q["q"], "choices": q["choices"], "points": q.get("points", 1)}
                          for q in qs]}


@app.post("/api/quiz/{lab_id}")
def api_quiz_post(request: Request, lab_id: str, body: QuizBody):
    user = user_of(request)
    mod = _lab_or_404(lab_id)
    qs = _quiz_questions(mod)
    if len(body.answers) != len(qs):
        raise HTTPException(400, "une réponse par question requise")
    results, score, max_score = [], 0, 0
    for q, a in zip(qs, body.answers):
        pts = int(q.get("points", 1))
        max_score += pts
        ok = a == q["answer"]
        if ok:
            score += pts
        results.append({"ok": ok, "points": pts if ok else 0,
                        "correct": q["answer"], "expl": q.get("expl", "")})
    res = {"lab": mod.id, "user": user, "kind": "quiz", "score": score, "max": max_score,
           "questions": results}
    from .moodle import SCORES
    SCORES.mkdir(parents=True, exist_ok=True)
    import time
    (SCORES / f"{time.strftime('%Y%m%d-%H%M%S')}-{user}-{mod.id}-quiz.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2))
    return res


@app.get("/api/progress")
def api_progress(request: Request):
    user = user_of(request)
    entries = []
    for f in sorted((ROOT / "var" / "scores").glob("*.json")) if (ROOT / "var" / "scores").is_dir() else []:
        try:
            d = json.loads(f.read_text())
        except Exception:  # noqa: BLE001
            continue
        if d.get("user") == user:
            lab = d["lab"] + ("-quiz" if d.get("kind") == "quiz" else "")
            entries.append({"ts": f.stem.split("-")[0] + " " + f.stem.split("-")[1],
                            "lab": lab, "score": d["score"], "max": d["max"]})
    best = {}
    for e in entries:
        if e["lab"] not in best or e["score"] > best[e["lab"]]["score"]:
            best[e["lab"]] = e
    return {"history": entries[::-1], "best": list(best.values())}


@app.websocket("/ws/term/{sid}/{node}")
async def ws_term(ws: WebSocket, sid: str, node: str):
    from itsdangerous import BadSignature
    cookie = ws.cookies.get("netsys_user")
    user = None
    if cookie:
        with contextlib.suppress(BadSignature):
            user = _serializer().loads(cookie)
    s = sessions.get(sid)
    if not user or not s or s["user"] != user:
        await ws.close(code=4403)
        return
    mod = MODULES.get(s["lab"])
    if not mod or node not in _deployed_topo(s, mod)["topology"]["nodes"]:
        await ws.close(code=4404)
        return
    await ws.accept()
    sessions.touch(sid)
    await terminal.serve(DOCKER, f"clab-{s['clab_name']}-{node}", ws)
    sessions.touch(sid)


@app.on_event("startup")
async def startup() -> None:
    with contextlib.suppress(Exception):  # hôte sans containerlab : liste quand même servie
        for name in sessions.gc_orphans():
            print(f"[launcher] orphelins purgés: {name}")
    asyncio.create_task(sessions.sweeper())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
