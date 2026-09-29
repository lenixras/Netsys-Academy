"""Tests pytest du labo M14 — ne pas modifier ce fichier."""

from netcalc import cidr_hosts, first_usable, mac_format, http_get_status


def test_cidr_hosts_chaine():
    assert cidr_hosts("10.0.0.0/24") == 254


def test_cidr_hosts_entier():
    assert cidr_hosts(28) == 14


def test_first_usable():
    assert first_usable("192.168.1.0/24") == "192.168.1.1"


def test_mac_format():
    assert mac_format("aa-bb-cc-dd-ee-ff") == "AA:BB:CC:DD:EE:FF"
    assert mac_format("0123456789ab") == "01:23:45:67:89:AB"


def test_http_status_ok():
    assert http_get_status("http://127.0.0.1:8000") == 200


def test_http_status_404():
    assert http_get_status("http://127.0.0.1:8000/inexistant.txt") == 404
