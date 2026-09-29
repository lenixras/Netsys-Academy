"""Orchestration containerlab. Sur cet hôte WSL2 sans sudo, CLAB_CMD=bin/clab-root
(conteneur privilégié) ; les labs sont déployés depuis des copies sous var/labs/."""
import os
import shlex
import shutil
import subprocess
from pathlib import Path

CLAB = shlex.split(os.environ.get("CLAB_CMD", "containerlab"))
LABS_DIR = Path(os.environ.get("LABS_DIR", "var/labs"))


def _docker(*args, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def deploy(topo_path: str, name: str) -> None:
    d = LABS_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    topo = (d / "topology.yaml").resolve()
    shutil.copyfile(topo_path, topo)
    r = subprocess.run(CLAB + ["deploy", "-t", str(topo), "--name", name],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        shutil.rmtree(d, ignore_errors=True)
        raise RuntimeError(f"containerlab deploy: {r.stderr[-1500:] or r.stdout[-1500:]}")


def destroy(name: str) -> None:
    # containerlab destroy -t ne correspond pas aux labs déployés avec --name ;
    # le label docker containerlab=<lab> est la source de vérité.
    ids = _docker("ps", "-aq", "--filter", f"label=containerlab={name}").stdout.split()
    if ids:
        r = _docker("rm", "-f", *ids)
        if r.returncode != 0:
            raise RuntimeError(f"docker rm: {r.stderr[-500:]}")
    # le sous-répertoire clab-<name>/ créé par containerlab est root-owned :
    # rmtree ignore_errors le laisse en place (quelques Ko, réécrits au prochain déploiement).
    shutil.rmtree(LABS_DIR / name, ignore_errors=True)


def list_lab_names() -> list[str]:
    r = _docker("ps", "--filter", "label=containerlab",
                "--format", '{{.Label "containerlab"}}', timeout=30)
    return sorted({line for line in r.stdout.splitlines() if line})


def orphan_session_names(known: set[str]) -> list[str]:
    """Labs 'session-*' vivants sur Docker sans ligne running en base."""
    return [n for n in list_lab_names() if n.startswith("session-") and n not in known]
