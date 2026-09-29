"""netcalc — utilitaires reseau pour le labo M14.

Complete les quatre fonctions ci-dessous (elles levent NotImplementedError
tant qu'elles ne sont pas ecrites). Puis lance :

    cd /root && python3 -m pytest -q test_netcalc.py

Indices : module standard `ipaddress` pour le CIDR, `re` pour le MAC,
`urllib.request` pour le HTTP (le serveur local tourne sur le port 8000).
"""

import ipaddress
import re
import urllib.error
import urllib.request


def cidr_hosts(prefix):
    """Nombre d'hotes utilisables d'un reseau.

    Accepte un prefix en entier (24) ou un CIDR en chaine ("10.0.0.0/24").
    Exemples : cidr_hosts("10.0.0.0/24") -> 254 ; cidr_hosts(28) -> 14.
    """
    raise NotImplementedError("a toi d'implementer cidr_hosts")


def first_usable(cidr):
    """Premiere adresse utilisable d'un CIDR, en chaine.

    Exemple : first_usable("192.168.1.0/24") -> "192.168.1.1".
    """
    raise NotImplementedError("a toi d'implementer first_usable")


def mac_format(mac):
    """Normalise une adresse MAC en "AA:BB:CC:DD:EE:FF" (majuscules).

    Accepte aa-bb-cc-dd-ee-ff, aabb.ccdd.eeff ou aabbccddeeff.
    """
    raise NotImplementedError("a toi d'implementer mac_format")


def http_get_status(url):
    """Code de statut HTTP (int) d'une requete GET sur url, via urllib.

    Un 404 doit revenir comme 404 (attraper urllib.error.HTTPError),
    pas lever une exception.
    """
    raise NotImplementedError("a toi d'implementer http_get_status")
