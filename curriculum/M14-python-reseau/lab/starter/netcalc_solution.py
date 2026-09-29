"""netcalc — version complete (correction du labo M14)."""

import ipaddress
import re
import urllib.error
import urllib.request


def cidr_hosts(prefix):
    """Nombre d'hotes utilisables : cidr_hosts(24) ou cidr_hosts("10.0.0.0/24")."""
    if isinstance(prefix, str):
        p = int(prefix.split("/")[1])
    else:
        p = int(prefix)
    return max(0, 2 ** (32 - p) - 2)


def first_usable(cidr):
    """Premiere adresse utilisable d'un CIDR, en chaine."""
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = list(net.hosts())
    return str(hosts[0]) if hosts else str(net.network_address)


def mac_format(mac):
    """Normalise une MAC en AA:BB:CC:DD:EE:FF (majuscules)."""
    h = re.sub(r"[^0-9a-fA-F]", "", mac).upper()
    if len(h) != 12:
        raise ValueError(f"MAC invalide: {mac!r}")
    return ":".join(h[i:i + 2] for i in range(0, 12, 2))


def http_get_status(url):
    """Code HTTP (int) d'un GET via urllib ; un 404 revient comme 404."""
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as err:
        return int(err.code)
