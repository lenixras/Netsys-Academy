"""Génère les modules M19-M26 (moule identique aux modules existants)."""
import base64
import json
import textwrap
from pathlib import Path

import yaml


def file_cmd(node, path, text):
    """Écrit un fichier dans le conteneur via base64 (robuste sous sh -c)."""
    return dict(node=node, cmd=f"echo {base64.b64encode(text.encode()).decode()} | base64 -d > {path}")

ROOT = Path(__file__).resolve().parent.parent / "curriculum"


def mod_dir(m):
    d = ROOT / m
    d.mkdir(exist_ok=True)
    (d / "lab").mkdir(exist_ok=True)
    return d


def dump(path, data):
    Path(path).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200))


def write(path, text):
    Path(path).write_text(textwrap.dedent(text).strip() + "\n")


MODULES = {}

# ---------------------------------------------------------------- M19
MODULES["M19-cisco-ios"] = dict(
    module=dict(
        id="M19",
        title="Cisco-like : CLI IOS sur routeur et routage inter-VLAN",
        wave=2,
        prereqs=["M5", "M6"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=45,
                 setup=[
                     dict(node="sw", cmd="ip link add br0 type bridge vlan_filtering 1 && ip link set br0 up"),
                     dict(node="sw", cmd="ip link set eth1 master br0 && ip link set eth2 master br0 && ip link set eth3 master br0 && ip link set eth1 up && ip link set eth2 up && ip link set eth3 up"),
                     dict(node="sw", cmd="bridge vlan add dev eth1 vid 10 pvid untagged && bridge vlan add dev eth2 vid 20 pvid untagged && bridge vlan add dev eth3 vid 10 tagged && bridge vlan add dev eth3 vid 20 tagged"),
                     dict(node="sw", cmd="bridge vlan del dev eth1 vid 1 && bridge vlan del dev eth2 vid 1 && bridge vlan del dev eth3 vid 1"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m19-ios",
        mgmt={"network": "clab-m19", "ipv4-subnet": "10.198.27.0/24"},
        topology=dict(
            nodes=dict(
                sw={"kind": "linux", "image": "netsys/labnode:2"},
                r1={"kind": "linux", "image": "netsys/frrlab:1"},
                h1={"kind": "linux", "image": "netsys/labnode:2"},
                h2={"kind": "linux", "image": "netsys/labnode:2"},
            ),
            links=[["h1:eth1", "sw:eth1"], ["h2:eth1", "sw:eth2"], ["sw:eth3", "r1:eth1"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="subif_vlan10", node="r1", cmd='ip -d link show eth1.10 2>/dev/null | grep -Ec "protocol 802.1Q +id 10"',
             expect="^1$", points=1,
             hint="eth1.10 n'existe pas : sous l'interface eth1, crée une sous-interface 802.1Q avec 'ip link add eth1.10 link eth1 type vlan id 10' puis 'ip link set eth1.10 up' (etape 1)."),
        dict(id="subif_vlan20", node="r1", cmd='ip -d link show eth1.20 2>/dev/null | grep -Ec "protocol 802.1Q +id 20"',
             expect="^1$", points=1,
             hint="Pareil pour le VLAN 20 : 'ip link add eth1.20 link eth1 type vlan id 20' puis 'ip link set eth1.20 up' (etape 1)."),
        dict(id="addr_vlan10_vtysh", node="r1", cmd='vtysh -c "show running-config" | grep -c "ip address 192.168.10.254/24"',
             expect="^1$", points=2,
             hint="L'adresse du VLAN 10 doit être déclarée dans FRR : vtysh -c 'conf t' -c 'interface eth1.10' -c 'ip address 192.168.10.254/24' (etape 2). C'est l'équivalent de 'interface eth1.10 / encapsulation dot1Q 10 / ip address ...' sur un vrai IOS Cisco."),
        dict(id="addr_vlan20_vtysh", node="r1", cmd='vtysh -c "show running-config" | grep -c "ip address 192.168.20.254/24"',
             expect="^1$", points=2,
             hint="Sous-interface eth1.20 déclarée dans FRR avec 'ip address 192.168.20.254/24' (etape 2)."),
        dict(id="h1_ping_h2", node="h1", cmd="ping -c2 -W2 192.168.20.1", expect="0% packet loss", points=3,
             hint="h1 doit joindre h2 a travers le routeur : h1 ip 192.168.10.1/24 avec route par defaut 192.168.10.254 ; h2 ip 192.168.20.1/24 avec route par defaut 192.168.20.254 (etape 3). Le routage inter-VLAN ne marche que si les deux sous-interface et leurs adresses sont actives (etapes 1-2)."),
        dict(id="write_memory", node="r1", cmd='grep -c "192.168.20.254" /etc/frr/zebra.conf',
             expect="^1$", points=1,
             hint="Sur Cisco on fait 'copy running-config startup-config' (ou 'write memory') ; ici vtysh -c 'write memory' doit creer /etc/frr/zebra.conf (mode traditional FRR) avec la config des adresses (etape 4)."),
    ]),
    theory="""
# M19 — Cisco-like : la CLI IOS, pour de vrai

## Pourquoi une « CLI Cisco » ?

Le marché du réseau parle Cisco. Les images IOS réelles ne sont pas
distribuables librement, mais la **syntaxe** IOS est un standard de fait.
Dans ce lab, le routeur tourne sous **FRRouting** dont la CLI `vtysh`
reprend presque mot pour mot le mode d'emploi IOS :

| Sur un Cisco IOS | Ici, sur FRR (vtysh) |
|---|---|
| `enable` → `configure terminal` | `vtysh` puis `conf t` |
| `interface GigabitEthernet0/1.10` | `interface eth1.10` |
| `encapsulation dot1Q 10` | l'interface VLAN est créée d'abord par Linux : `ip link add eth1.10 link eth1 type vlan id 10` |
| `ip address 192.168.10.254 255.255.255.0` | `ip address 192.168.10.254/24` |
| `no shutdown` | FRR active l'interface quand l'interface Linux est `up` |
| `show running-config` | `vtysh -c "show running-config"` |
| `copy run start` / `write memory` | `vtysh -c "write memory"` → `/etc/frr/zebra.conf` (un fichier par démon, mode traditional) |

## Routage inter-VLAN « router on a stick »

Un switch (pré-câblé ici) porte deux VLANs : VLAN 10 (192.168.10.0/24, h1) et
VLAN 20 (192.168.20.0/24, h2). Un seul lien relie le switch au routeur, en
**tronk** (trunk) : les trames gardent leur tag 802.1Q. Le routeur ouvre donc
deux **sous-interfaces**, une par VLAN :

```text
eth1      lien physique vers le trunk du switch
eth1.10   tag VLAN 10 → ip 192.168.10.254/24  (passerelle de h1)
eth1.20   tag VLAN 20 → ip 192.168.20.254/24  (passerelle de h2)
```

Un paquet de h1 vers h2 traverse : h1 → tag10 → routeur (dé-tag, routage,
re-tag 20) → h2. C'est exactement ce que font les switches 3 couches Cisco,
sauf qu'ici le routage est visible et modifiable à la main.

## Les 4 étapes du lab

1. Créer les sous-interface VLAN sur le routeur (`ip link add ... type vlan`).
2. Leur donner une adresse IP dans FRR (`conf t` → `interface eth1.10` …).
3. Configurer h1 et h2 (adresse IP + route par défaut vers leur passerelle).
4. Sauver la config (`write memory`) comme on ferait `copy run start`.

## À retenir

- Le VLAN sépare au niveau 2 ; seule une passerelle L3 relie les sous-réseaux.
- Trunk = lien porteur de plusieurs VLANs, tags 802.1Q.
- La CLI réseau (IOS/FRR) ne configure pas le noyau directement : sur Linux,
  l'objet réseau (sous-interface, pont, route) doit exister AVANT que FRR le nomme.
""",
    quiz=dict(questions=[
        dict(q="Que fait la commande Cisco 'encapsulation dot1Q 10' sur une sous-interface ?",
             choices=["Elle allume le port", "Elle attache les trames de cette sous-interface au VLAN 802.1Q 10", "Elle chiffre le trafic", "Elle crée un route statique"],
             answer=1, points=1,
             expl="Le tag 802.1Q identifie le VLAN dans la trame ; la sous-interface n'émet/accepte que les trames taguées avec ce VLAN."),
        dict(q="Un lien 'trunk' entre un switch et un routeur sert à :",
             choices=["Augmenter le débit", "Transporter plusieurs VLANs sur un seul câble physique", "Isoler le management", "Faire du LACP"],
             answer=1, points=1,
             expl="Le trunk porte les trames taguées de chaque VLAN, ce qui permet le 'router on a stick' avec un seul câble."),
        dict(q="Quelle commande FRR sauvegarde la config au démarrage, comme 'copy run start' ?",
             choices=["write memory", "save /e", "copy startup running", "commit"],
             answer=0, points=1,
             expl="vtysh 'write memory' (alias copy running-config startup-config) écrit /etc/frr/frr.conf."),
        dict(q="Pourquoi le routeur a-t-il besoin de 'ip link add eth1.10 link eth1 type vlan id 10' AVANT la config vtysh ?",
             choices=["C'est décoratif", "FRR ne crée pas le dispositif réseau du noyau : l'interface doit exister dans Linux", "Sinon le switch ne répond pas", "Pour activer le DHCP"],
             answer=1, points=1,
             expl="FRR est un daemon de routage : il configure ce que le noyau expose. La sous-interface 802.1Q est un objet du noyau Linux."),
        dict(q="h1 (VLAN 10) veut joindre h2 (VLAN 20). Qui fait le routage ?",
             choices=["Le switch, toujours", "La passerelle L3 (le routeur) sur l'adresse du VLAN de h1", "h2 directement", "Personne, c'est impossible"],
             answer=1, points=1,
             expl="Le trafic passe par la default gw de h1, c'est-à-dire l'adresse .254 du VLAN 10 sur le routeur, qui relaye vers le VLAN 20."),
        dict(q="Quel équivalent Cisco de 'no shutdown' est juste ici ?",
             choices=["ip link set up", "Le port FRR monte dès que l'interface Linux correspondante est up", "interface vlan", "carrier detect"],
             answer=1, points=1,
             expl="FRR n'éteint pas d'interface : l'état vient de Linux ; 'no shutdown' côté IOS agit sur le port lui-même."),
    ]),
    scenario="""
# Scénario — Le stage de remise à niveau réseau

Vous rejoignez une PME qui vient d'acheter des « switches Cisco » et un
« routeur Linux ». Le document d'archi promet : deux services (VLAN 10
Bureau, VLAN 20 Labo), un seul câble vers le routeur, et une config qui
survit au redémarrage.

Le switch est déjà programmé (VLANs + trunk). Il vous reste :

1. Créer les sous-interfaces VLAN du routeur.
2. Leur donner les adresses passerelles (192.168.10.254/24, 192.168.20.254/24) via vtysh.
3. Régler les deux postes (IP + passerelle) pour qu'ils se joignent.
4. Sauver la config du routeur (`write memory`) — l'auditeur de sécurité
   vérifiera que `show running-config` et le fichier sauvegardé concordent.

Ouvrez le terminal du routeur (clic sur le nœud r1) : `vtysh` vous attend,
avec le vocabulaire IOS que vous connaissez déjà.
""",
    solve={
        "r1": ["ip link set eth1 up",
               "ip link add eth1.10 link eth1 type vlan id 10",
               "ip link add eth1.20 link eth1 type vlan id 20",
               "ip link set eth1.10 up",
               "ip link set eth1.20 up",
               "vtysh -c 'conf t' -c 'interface eth1.10' -c 'ip address 192.168.10.254/24' -c 'interface eth1.20' -c 'ip address 192.168.20.254/24' -c 'end'",
               "vtysh -c 'write memory'"],
        "h1": ["ip addr add 192.168.10.1/24 dev eth1", "ip link set eth1 up", "ip route replace default via 192.168.10.254"],
        "h2": ["ip addr add 192.168.20.1/24 dev eth1", "ip link set eth1 up", "ip route replace default via 192.168.20.254"],
    },
)

# ---------------------------------------------------------------- M20
MODULES["M20-ipv6"] = dict(
    module=dict(
        id="M20",
        title="IPv6 en pratique : adresses, SLAAC et routage",
        wave=2,
        prereqs=["M1", "M8"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=30,
                 setup=[
                     dict(node="r1", cmd="sysctl -qw net.ipv6.conf.all.forwarding=1"),
                     dict(node="r1", cmd="ip -6 addr add 2001:db8:acad:1::1/64 dev eth1 && ip -6 addr add 2001:db8:acad:2::1/64 dev eth2 && ip link set eth1 up && ip link set eth2 up"),
                     dict(node="h1", cmd="sysctl -qw net.ipv6.conf.eth1.accept_ra=1 && sysctl -qw net.ipv6.conf.all.accept_ra=1 && ip link set eth1 up"),
                     dict(node="r1", cmd="echo '# Ecrire /etc/radvd.conf pour annoncer le prefixe 2001:db8:acad:1::/64 sur eth1' > /root/CONSIGNE.txt"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m20-ipv6",
        mgmt={"network": "clab-m20", "ipv4-subnet": "10.198.28.0/24"},
        topology=dict(
            nodes=dict(
                r1={"kind": "linux", "image": "netsys/labnode:3"},
                h1={"kind": "linux", "image": "netsys/labnode:3"},
            ),
            links=[["r1:eth1", "h1:eth1"], ["r1:eth2", "h1:eth2"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="radvd_running", node="r1", cmd="pgrep -x radvd",
             points=2,
             hint="Le routeur n'annonce rien : ecrire /etc/radvd.conf (interface eth1 { AdvSendAdvert on; prefix 2001:db8:acad:1::/64 {}; };) puis lancer 'radvd' (etape 1)."),
        dict(id="slaac_h1", node="h1", cmd='ip -6 addr show dev eth1 scope global | grep -c "2001:db8:acad:1:"',
             expect="^1$", points=2,
             hint="h1 doit obtenir une adresse SLAAC dans 2001:db8:acad:1::/64 grace aux RA de radvd : verifier 'radvd -c /etc/radvd.conf' (syntaxe), puis 'ip -6 addr show dev eth1' sur h1 (etape 1)."),
        dict(id="h1_ping_gateway", node="h1", cmd="ping -6 -c2 -W2 2001:db8:acad:1::1", expect="0% packet loss", points=2,
             hint="Ping6 vers la passerelle : l'adresse SLAAC (etape 1) doit etre presente et le lien up. Si 'unreachable', verifier que l'adresse de r1 est bien 2001:db8:acad:1::1/64 sur eth1."),
        dict(id="static_route_lan2", node="h1", cmd='ip -6 route show | grep -c "2001:db8:acad:2::/64"',
             expect="^1$", points=1,
             hint="La deuxieme LAN (2001:db8:acad:2::/64) n'est pas dans la table : ajouter 'ip -6 route add 2001:db8:acad:2::/64 via 2001:db8:acad:1::1' sur h1 (etape 2)."),
        dict(id="h1_ping_lan2", node="h1", cmd="ping -6 -c2 -W2 2001:db8:acad:2::1", expect="0% packet loss", points=3,
             hint="Le test final passe quand la route statique v6 existe (etape 2) et que la passerelle repond. Controle avec 'ip -6 route get 2001:db8:acad:2::1' sur h1."),
    ]),
    theory="""
# M20 — IPv6 en pratique

## L'adresse IPv6 en 60 secondes

- 128 bits, écriture hexadécimale en 8 groupes séparés par `:` ; `::` remplace
  les zéros consécutifs (une seule fois).
- Préfixe = l'équivalent du CIDR : `2001:db8:acad:1::/64` = sous-réseau 64 bits.
- `2001:db8::/32` est le bloc réservé à la documentation — nos labs l'utilisent.
- Chaque interface a plusieurs adresses : link-local `fe80::/10` (toujours là),
  globale, et multicast.

## SLAAC : « pas de DHCP, ça suffit »

Sans serveur, une machine se configure seule :

1. Elle génère une adresse link-local (`fe80::` + identifiant d'interface).
2. Elle envoie une **RS** (Router Solicitation) sur le lien.
3. Le routeur répond **RA** (Router Advertisement) : « le préfixe est
   2001:db8:acad:1::/64, autonome ».
4. La machine colle le préfixe + son IID → adresse globale.

Le logiciel qui envoie les RA s'appelle **radvd** — l'équivalent du « DHCP
server » de IPv6, sans état, sans baux.

## Routage IPv6

Comme en v4, une route indique quel next-hop joindre :

```text
ip -6 route add 2001:db8:acad:2::/64 via 2001:db8:acad:1::1
ip -6 route get 2001:db8:acad:2::1     # la même vue que 'ip route'
```

À retenir : en v6 **pas de NAT** aux frontières du cours — chaque machine a
une adresse globale routable. C'est le retour du modèle bout-à-bout.

## Les étapes du lab

1. Sur r1 : écrire `/etc/radvd.conf` qui annonce le préfixe du LAN sur eth1,
   valider (`radvd -c /etc/radvd.conf`) puis lancer `radvd`.
2. Sur h1 : vérifier que l'adresse SLAAC est apparue, puis ajouter la route
   statique vers le second LAN du routeur.
3. Tester `ping -6` : passerelle puis LAN2.
""",
    quiz=dict(questions=[
        dict(q="Combien de bits dans une adresse IPv6 ?",
             choices=["32", "64", "128", "256"], answer=2, points=1,
             expl="128 bits, soit 8 groupes hexadécimaux de 16 bits."),
        dict(q="A quoi sert une adresse link-local fe80::/10 ?",
             choices=["Elle route sur Internet", "Elle sert aux voisins immédiats : ND, RA et next-hop des routes", "Elle remplace le DNS", "Elle chiffre le lien"],
             answer=1, points=1,
             expl="Toute interface v6 a une fe80:: ; les protocoles de voisinage et les routes y référencent le next-hop."),
        dict(q="Que signifie 'autonomous' dans un préfixe annoncé par RA ?",
             choices=["Le préfixe est public", "Les hôtes peuvent former leurs adresses par SLAAC", "Pas de route statique", "DHCPv6 obligatoire"],
             answer=1, points=1,
             expl="Le flag A du RA autorise la construction auto de l'adresse globale à partir du préfixe."),
        dict(q="radvd joue le rôle de :",
             choices=["Serveur DNS", "Annonceur de RA (l'« hôte DHCP » stateless de IPv6)", "Pare-feu", "Refroidisseur de caches"],
             answer=1, points=1,
             expl="radvd envoie les RA : préfixes, drapeaux et durée de vie. Il ne gère aucun bail."),
        dict(q="Comment écrire en forme raccourcie 2001:0db8:0000:0000:0000:0000:0000:0001 ?",
             choices=["2001:db8::1", "2001:db8:0:0:0:0:0:1 uniquement", "2001::db8:1", "2001:db8:::1"],
             answer=0, points=1,
             expl="On retire les zéros tête de groupe et un seul '::' compacte les groupes nuls."),
        dict(q="En IPv6, le NAT (« masquerade ») est :",
             choices=["Obligatoire", "Inutile dans le modèle du cours : on a des adresses globales pour tout le monde", "Plus rapide qu'en v4", "Géré par radvd"],
             answer=1, points=1,
             expl="Le stock d'adresses v6 rend le NAT superflu aux frontières ; on segmente par filtrage, pas par traduction."),
    ]),
    scenario="""
# Scénario — La migration IPv6 du labo

Votre labo a reçu le préfixe documentation `2001:db8:acad::/48` :
LAN1 = `:1::/64` (les machines), LAN2 = `:2::/64` (le serveur de calcul,
ici une adresse du routeur). Pas de DHCPv6 : la direction veut du SLAAC pur.

Objectifs :
1. Faire annoncer LAN1 par le routeur (radvd).
2. Vérifier que la machine h1 s'auto-configura (adresse SLAAC).
3. Atteindre LAN2 depuis h1 avec une route statique v6.
4. Rejouer le « ping » de toujours : `ping -6`, en gardant un oeil sur
   `ip -6 neighbor` (l'équivalent de l'ARP, en plus propre).
""",
    solve={
        "r1": ["printf 'interface eth1 {\\n  AdvSendAdvert on;\\n  prefix 2001:db8:acad:1::/64 {};\\n};\\n' > /etc/radvd.conf", "radvd"],
        "h1": ["for i in 1 2 3 4 5 6; do ip -6 route add 2001:db8:acad:2::/64 via 2001:db8:acad:1::1 && break; sleep 2; done"],
    },
)

# ---------------------------------------------------------------- M21
MODULES["M21-bgp"] = dict(
    module=dict(
        id="M21",
        title="BGP : faire parler deux organisations",
        wave=3,
        prereqs=["M6"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=45,
                 setup=[
                     dict(node="r1", cmd="ip link set eth1 up && ip link set eth2 up && vtysh -c 'conf t' -c 'interface eth1' -c 'ip address 10.0.21.1/29' -c 'interface eth2' -c 'ip address 10.21.1.1/24' -c 'end'"),
                     dict(node="r2", cmd="ip link set eth1 up && ip link set eth2 up && vtysh -c 'conf t' -c 'interface eth1' -c 'ip address 10.0.21.2/29' -c 'interface eth2' -c 'ip address 10.21.2.1/24' -c 'end'"),
                     dict(node="r1", cmd="sysctl -qw net.ipv4.ip_forward=1"),
                     dict(node="r2", cmd="sysctl -qw net.ipv4.ip_forward=1"),
                     dict(node="h1", cmd="ip addr add 10.21.1.10/24 dev eth1 && ip link set eth1 up && ip route replace default via 10.21.1.1"),
                     dict(node="h2", cmd="ip addr add 10.21.2.10/24 dev eth1 && ip link set eth1 up && ip route replace default via 10.21.2.1"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m21-bgp",
        mgmt={"network": "clab-m21", "ipv4-subnet": "10.198.29.0/24"},
        topology=dict(
            nodes=dict(
                r1={"kind": "linux", "image": "netsys/frrlab:2"},
                r2={"kind": "linux", "image": "netsys/frrlab:2"},
                h1={"kind": "linux", "image": "netsys/labnode:1"},
                h2={"kind": "linux", "image": "netsys/labnode:1"},
            ),
            links=[["r1:eth1", "r2:eth1"], ["r1:eth2", "h1:eth1"], ["r2:eth2", "h2:eth1"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="peer_estab_r1", node="r1", cmd="vtysh -c 'show bgp summary' | grep '^10.0.21.2' | grep -vcE '(Active|Idle|Connect|Admin|Policy)'",
             expect="^1$", points=2,
             hint="Pas de session BGP etablie avec r2 : 'vtysh -c ''conf t'' -c ''router bgp 64512'' -c ''no bgp ebgp-requires-policy'' -c ''neighbor 10.0.21.2 remote-as 64513'' -c end'. L'etat doit devenir un nombre de prefixes recu (Established). FRR bloque par defaut les echanges eBGP sans politique : 'no bgp ebgp-requires-policy' = le comportement Cisco par defaut."),
        dict(id="peer_estab_r2", node="r2", cmd="vtysh -c 'show bgp summary' | grep '^10.0.21.1' | grep -vcE '(Active|Idle|Connect|Admin|Policy)'",
             expect="^1$", points=2,
             hint="Symetrique chez r2 : router bgp 64513 + no bgp ebgp-requires-policy + neighbor 10.0.21.1 remote-as 64512."),
        dict(id="route_net_h2_in_r1", node="r1", cmd='vtysh -c "show ip route bgp" | grep -c "10.21.2.0/24"',
             expect="^1$", points=2,
             hint="r1 doit APPRENDRE le LAN de r2 : c'est r2 qui doit annoncer 'network 10.21.2.0/24' sous 'router bgp 64513' (avec address-family ipv4 unicast chez FRR : 'vtysh -c conf t -c ''router bgp 64513'' -c ''address-family ipv4 unicast'' -c ''network 10.21.2.0/24'' -c end)."),
        dict(id="route_net_h1_in_r2", node="r2", cmd='vtysh -c "show ip route bgp" | grep -c "10.21.1.0/24"',
             expect="^1$", points=2,
             hint="Pareil pour 10.21.1.0/24 announce par r1 dans 'router bgp 64512'."),
        dict(id="ping_h1_h2", node="h1", cmd="ping -c2 -W2 10.21.2.10", expect="0% packet loss", points=3,
             hint="Le ping h1->h2 passe quand les deux routes BGP existent (les checks precedents) et que le transit est autorise (ip_forward deja en place). Verifier 'ip route | grep 10.21.2' sur r1 : la route doit aussi etre INSTALLEE dans le noyau par zebra."),
    ]),
    theory="""
# M21 — BGP : le protocole d'Internet

## À quoi sert BGP ?

OSPF (M6) fait parler les routeurs **d'une même organisation** (un « AS »).
BGP relie les organisations entre elles : FAI, grandes entreprises, datacenters.
Chaque AS possède un **numéro d'AS** (ex. 64512) et annonce ses **préfixes**
(« mes réseaux sont 10.21.1.0/24 ») à ses voisins, appelés **pairs** (*peers*).

## eBGP en 5 commandes

Sur r1 (AS 64512), parler à r2 (AS 64513) :

```text
router bgp 64512
 neighbor 10.0.21.2 remote-as 64513
 address-family ipv4 unicast
  network 10.21.1.0/24
```

- `neighbor ... remote-as` = qui est mon voisin et son AS.
- `network ...` = mes préfixes, **seulement s'ils existent déjà dans la table**
  (ici connectés via eth2).
- FRR utilise les *address-families* ; Cisco IOS place `network` sans ce niveau.
- FRR **bloque par défaut** l'échange eBGP sans politique configurée (`ebgp-requires-policy`) : sur un lab sans route-map, ajoutez `no bgp ebgp-requires-policy` — IOS, lui, annonce par défaut.

## Pourquoi « Established » ?

La session TCP (port 179) doit s'établir ; les colonnes de
`show bgp summary` : état = Established et compteur de préfixes reçus.
Un voisin bloqué en `Active` = IP injoignable, AS numéro trompé, ou route
manquante vers le pair.

## Le chemin, pas la distance

BGP ne choisit pas « le moins de sauts » : il choisit selon la **politique**.
L'attribut central est l'**AS_PATH** : la liste des AS traversés. En pratique :
préfixe appris par un voisin du même AS (iBGP) → préféré, sinon le plus court
AS_PATH, etc. Un `local-pref` ou un `MED` peuvent tordre la sélection —
c'est exactement ce que les opérateurs vendent (« le transit moins cher »).

## Étapes du lab

1. Sur chaque routeur : `router bgp <mon-as>` + `neighbor <pair> remote-as <leur-as>`.
2. Annoncer son LAN avec `network` dans l'address-family ipv4 unicast.
3. Vérifier `show bgp summary` (Established), `show ip route bgp` (les routes),
   puis ping h1 → h2.
""",
    quiz=dict(questions=[
        dict(q="BGP sert principalement à :",
             choices=["Router dans une salle serveur", "Échanger des préfixes entre systèmes autonomes (organisations)", "Remplacer le DNS", "Filtrer les broadcasts"],
             answer=1, points=1,
             expl="BGP = le protocole d'inter-domaine : il relie les AS, chacun contrôlant ses annonces."),
        dict(q="Que signifie un pair bloqué en état 'Active' ?",
             choices=["Session établie", "La connexion TCP vers le pair n'aboutit pas (IP/voisinage/ACL)", "Trop de préfixes", "Le routeur redémarre"],
             answer=1, points=1,
             expl="Active = on retente sans succès : pas de route vers le pair, mauvais numéro d'AS ou port 179 filtré."),
        dict(q="La commande 'network 10.21.1.0/24' annonce le préfixe seulement si :",
             choices=["Le préfixe existe déjà dans la table de routage interne", "bgpd est redémarré", "Le voisin est en iBGP", "On a configuré OSPF"],
             answer=0, points=1,
             expl="BGP ne publie que ce que le routeur route déjà : ici le LAN connecté d'eth2 satisfait la condition."),
        dict(q="Quel attribut BGP liste les AS traversés par une annonce ?",
             choices=["MED", "AS_PATH", "ORIGIN", "NEXT_HOP"],
             answer=1, points=1,
             expl="AS_PATH est la colonne vertébrale de la boucle-anti et du choix de chemin."),
        dict(q="Sur le port TCP, BGP écoute sur :",
             choices=["179", "520", "89", "161"],
             answer=0, points=1,
             expl="La session BGP = TCP/179, d'où l'importance de la reachabilité IP avant tout le reste."),
        dict(q="Un AS privé (utilisable sans numéro officiel) parmi ceux-ci :",
             choices=["64512", "1", "100", "8000"],
             answer=0, points=1,
             expl="Les plages privées 64512-65534 et 4201024000+ sont réservées ; 64512 est notre AS de lab."),
    ]),
    scenario="""
# Scénario — Les deux datacenters veulent se joindre

Votre entreprise (AS 64512, LAN 10.21.1.0/24 derrière r1) vient de louer une
baie chez un voisin (AS 64513, LAN 10.21.2.0/24 derrière r2). Un seul lien
les relie (10.0.21.0/29, vos IP .1 et .2 déjà posées).

Le plan d'adressage des LAN et des passerelles est déjà appliqué. À vous :
1. Ouvrir la session eBGP entre les deux AS.
2. Annoncer à chaque AS son LAN.
3. Prouver la jointure : h1 (10.21.1.10) ping h2 (10.21.2.10), et les routes
   BGP installées dans le noyau des deux routeurs.
""",
    solve={
        "r1": ["vtysh -c 'conf t' -c 'router bgp 64512' -c 'no bgp ebgp-requires-policy' -c 'neighbor 10.0.21.2 remote-as 64513' -c 'address-family ipv4 unicast' -c 'network 10.21.1.0/24' -c 'end'"],
        "r2": ["vtysh -c 'conf t' -c 'router bgp 64513' -c 'no bgp ebgp-requires-policy' -c 'neighbor 10.0.21.1 remote-as 64512' -c 'address-family ipv4 unicast' -c 'network 10.21.2.0/24' -c 'end'"],
    },
)

# ---------------------------------------------------------------- M22
NAMED_CONF = textwrap.dedent("""\
    options {
        directory "/var/cache/bind";
        listen-on port 53 { any; };
        allow-query { any; };
        allow-transfer { none; };
        recursion no;
    };
    zone "lab22.local" { type master; file "/root/db.lab22.local"; };
    zone "0.22.10.in-addr.arpa" { type master; file "/root/db.0.22.10"; };
""")
DB_FWD = textwrap.dedent("""\
    $TTL 3600
    @   IN  SOA ns.lab22.local. admin.lab22.local. (
          2026092801 ; serial
          3600 600 604800 60 )
        IN  NS  ns.lab22.local.
    ns  IN  A   10.22.1.1
    web IN  A   10.22.0.99
""")
DB_REV = textwrap.dedent("""\
    $TTL 3600
    @   IN  SOA ns.lab22.local. admin.lab22.local. (
          2026092801 ; serial
          3600 600 604800 60 )
        IN  NS  ns.lab22.local.
    99  IN  PTR web.lab22.local.
""")
REC_NAMED_CONF = textwrap.dedent("""\
    options {
        directory "/var/cache/bind";
        listen-on port 53 { any; };
        allow-query { any; };
        recursion yes;
        allow-recursion { any; };
    };
    zone "lab22.local" { type slave; masters { 10.22.1.1; }; file "lab22.local.slave"; };
    zone "0.22.10.in-addr.arpa" { type slave; masters { 10.22.1.1; }; file "0.22.10.slave"; };
""")

MODULES["M22-dns-avance"] = dict(
    module=dict(
        id="M22",
        title="DNS avancé : zones secondaires, transferts et délégation",
        wave=3,
        prereqs=["M4"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=45,
                 setup=[
                     dict(node="auth", cmd="ip addr add 10.22.1.1/24 dev eth1 && ip link set eth1 up"),
                     dict(node="rec", cmd="ip addr add 10.22.1.2/24 dev eth2 && ip addr add 10.22.0.2/24 dev eth1 && ip link set eth1 up && ip link set eth2 up"),
                     dict(node="cli", cmd="ip addr add 10.22.0.30/24 dev eth1 && ip link set eth1 up && echo nameserver 10.22.0.2 > /etc/resolv.conf"),
                     file_cmd("auth", "/root/named.conf", NAMED_CONF),
                     file_cmd("auth", "/root/db.lab22.local", DB_FWD),
                     file_cmd("auth", "/root/db.0.22.10", DB_REV),
                     dict(node="auth", cmd="mkdir -p /var/cache/bind"),
                     dict(node="auth", cmd="named -c /root/named.conf -g > /root/named.log 2>&1 &"),
                     dict(node="rec", cmd="mkdir -p /var/cache/bind"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m22-dns",
        mgmt={"network": "clab-m22", "ipv4-subnet": "10.198.30.0/24"},
        topology=dict(
            nodes=dict(
                auth={"kind": "linux", "image": "netsys/labnode:3"},
                rec={"kind": "linux", "image": "netsys/labnode:3"},
                cli={"kind": "linux", "image": "netsys/labnode:3"},
            ),
            links=[["cli:eth1", "rec:eth1"], ["rec:eth2", "auth:eth1"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="auth_allows_transfer", node="auth", cmd='grep -c "10.22.1.2" /root/named.conf',
             expect="^[1-9]$", points=1,
             hint="Le maitre refuse le transfert vers le secondaire : editer /root/named.conf et remplacer 'allow-transfer { none; };' par 'allow-transfer { 10.22.1.2; };' puis recharger : pkill -x named; named -c /root/named.conf -g > /root/named.log 2>&1 & (etape 1)."),
        dict(id="named_rec_up", node="rec", cmd="pgrep -x named",
             points=2,
             hint="Le resolviseur secondaire ne tourne pas : ecrire /root/named.conf (options recursion yes; allow-recursion { any; }; directory /var/cache/bind + les deux zones 'type slave' vers master 10.22.1.1) puis named -c /root/named.conf -g > /root/named.log 2>&1 & (etape 2)."),
        dict(id="slave_db_sync", node="rec", cmd="grep -c web /var/cache/bind/lab22.local.slave 2>/dev/null || grep -rc web /var/cache/bind/",
             expect="^[1-9]", points=2,
             hint="Le transfert AXFR n'a rien ecrit : le nom du fichier de zone 'type slave' doit etre relatif (lab22.local.slave), le maitre doit autoriser le transfert (check precedent) et le serial doit concorder. Verifier /var/cache/bind/ puis named.log."),
        dict(id="dig_fwd_via_rec", node="cli", cmd='dig @10.22.0.2 web.lab22.local +short | grep -c "^10.22.0.99$"',
             expect="^1$", points=2,
             hint="rec doit repondre 10.22.0.99 pour web.lab22.local : tester d'abord 'named-checkconf /root/named.conf', verifier que les deux zones slave sont declarees et qu'aucune erreur AXFR ne figure dans /root/named.log (etape 2)."),
        dict(id="dig_rev_via_rec", node="cli", cmd='dig @10.22.0.2 -x 10.22.0.99 +short | grep -c "web.lab22.local"',
             expect="^1$", points=2,
             hint="La zone inverse 0.22.10.in-addr.arpa doit aussi etre dupliquee en slave sur rec (deuxieme bloc zone dans /root/named.conf, fichier db distinct)."),
    ]),
    theory="""
# M22 — DNS avancé

## Le DNS n'est pas une base unique

Un nom n'est « possédé » que par ses **serveurs faisant autorité** (ici `auth`).
Tout le reste n'est que copie : cache, zone secondaire, ou délégation.

- **Type de zone chez BIND** : `master` (l'original), `slave` (copie par
  transfert AXFR), `forward` (on ne fait que relayer).
- **Transfert AXFR** : le secondaire demande « donne-moi la zone version N ».
  Le maitre refuse tout le monde par défaut (`allow-transfer { none; }`) —
  on ouvre uniquement vers les IP des secondaires.
- **Serial (SOA)** : changer un enregistrement **sans incrémenter le serial**
  = les secondaires ne rattrapent pas. C'est l'erreur de prod nº1 du DNS.
- **Zone inverse** (`in-addr.arpa`) : même mécanisme, sens inverse
  adresse → nom, indispensable pour le PTR (antispam, diagnostics).

## Et la « récursion » ?

Un serveur récursif (`recursion yes`) part des racines et suit les délégations
NS/glue pour vous. Pour un client, `rec` est « son DNS » ; `auth` est
« l'autorité du nom ». Ce lab vous fait jouer les deux rôles : secondaire
esclave de `auth`, et resolviseur interrogé par `cli`.

## Étapes du lab

1. `auth` : autoriser le transfert AXFR vers 10.22.1.2 (et recharger named).
2. `rec` : écrire `/root/named.conf` — options récursives (recursion yes,
   allow-recursion { any; }) + les deux zones `type slave` masters 10.22.1.1 —
   puis lancer named.
3. `cli` : `dig @10.22.0.2 web.lab22.local` et `dig @10.22.0.2 -x 10.22.0.99`.
""",
    quiz=dict(questions=[
        dict(q="Un serveur 'master' d'une zone :",
             choices=["Ne fait que relayer", "Est la source de vérité où l'on édite les enregistrements", "Reçoit par AXFR", "Est obligatoire chez tous les domaines"],
             answer=1, points=1,
             expl="Le master porte l'original ; les secondaires s'alignent par transfert."),
        dict(q="Le transfert AXFR est :",
             choices=["La copie complète d'une zone vers un secondaire", "La compression des réponses", "Le chiffrement DNS", "Un type de cache"],
             answer=0, points=1,
             expl="AXFR = téléchargement intégral de la zone — donc on l'autorise au compte-gouttes (allow-transfer)."),
        dict(q="On ajoute un enregistrement sur le master mais le secondary ne change pas. Cause n°1 ?",
             choices=["Le TTL est trop bas", "Le serial SOA n'a pas été incrémenté", "Le firewall UDP", "Le DNSSEC manque"],
             answer=1, points=1,
             expl="Le secondary compare les serials : sans incrément, il estime sa copie à jour."),
        dict(q="La zone inverse de 10.22.0.0/24 s'écrit :",
             choices=["0.22.10.in-addr.arpa", "22.0.10.in-addr.arpa", "arpa.10.22.0", "reverse.10.22.0"],
             answer=0, points=1,
             expl="L'IPv4 se lit à l'envers par octets, suffixée .in-addr.arpa."),
        dict(q="allow-recursion { 10.0.0.0/8; } sur un serveur récursif :",
             choices=["Autorise uniquement ces clients à interroger le serveur en récursif", "Filtre les noms", "Empêche le cache", "Interdit le transfert"],
             answer=0, points=1,
             expl="Un open resolver (tout le monde) devient une arme de réflexion : on limite la récursion aux clients légitimes."),
        dict(q="Sur un client, 'nameserver' dans /etc/resolv.conf désigne :",
             choices=["L'autorité de zone", "Le serveur auquel on pose les questions (souvent récursif)", "Le serveur DHCP", "Le passe-relle"],
             answer=1, points=1,
             expl="Le client interroge son resolviseur ; celui-ci trouve l'autorité, pas le client."),
    ]),
    scenario="""
# Scénario — « Le DNS officiel doit survivre »

Le prestataire qui hébergeait votre DNS `lab22.local` coupe l'accès dans
30 jours. Vous dupliquez : `auth` (le maitre historique, déjà peuplé avec
web.lab22.local et son PTR) aura bientôt un secondaire `rec` — lui-même
aussi resolviseur des clients du LAN.

Votre mission avant le basculement :
1. Autoriser `auth` à transférer la zone vers `rec` (10.22.1.2), uniquement.
2. Sur `rec`, monter deux zones esclave (avant + inverse) et la récursion
   pour le LAN.
3. Depuis `cli`, prouver : `dig web.lab22.local` → 10.22.0.99 et
   `dig -x 10.22.0.99` → web.lab22.local, en passant bien par rec.
4. Bonus post-mortem : quel champ du fichier de zone déclenche la
   resynchronisation d'un secondaire ?
""",
    solve={
        "auth": ["sed -i \"s/allow-transfer { none; };/allow-transfer { 10.22.1.2; };/\" /root/named.conf", "pkill -x named; sleep 1; named -c /root/named.conf -g > /root/named.log 2>&1 &"],
        "rec": [f"echo {base64.b64encode(REC_NAMED_CONF.encode()).decode()} | base64 -d > /root/named.conf", "named -c /root/named.conf -g > /root/named.log 2>&1 &"],
    },
)

# ---------------------------------------------------------------- M23
SLAPD_CONF = textwrap.dedent("""\
    include /etc/ldap/schema/core.schema
    include /etc/ldap/schema/cosine.schema
    include /etc/ldap/schema/inetorgperson.schema
    pidfile /tmp/slapd.pid
    modulepath /usr/lib/ldap
    moduleload back_mdb
    database mdb
    maxsize 1073741824
    suffix "dc=lab23,dc=local"
    rootdn "cn=admin,dc=lab23,dc=local"
    rootpw secret
    directory /var/lib/ldap
    index objectClass eq
""")
BASE_LDIF = textwrap.dedent("""\
    dn: dc=lab23,dc=local
    objectClass: domain
    dc: lab23

    dn: ou=People,dc=lab23,dc=local
    objectClass: organizationalUnit
    ou: People

    dn: uid=elev1,ou=People,dc=lab23,dc=local
    objectClass: inetOrgPerson
    uid: elev1
    cn: Eleve Premier
    sn: Premier
    userPassword: elev1pass
""")

MODULES["M23-ldap"] = dict(
    module=dict(
        id="M23",
        title="LDAP : un annuaire pour centraliser les identités",
        wave=3,
        prereqs=["M3", "M4"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=45,
                 setup=[
                     dict(node="srv", cmd="ip addr add 10.23.0.10/24 dev eth1 && ip link set eth1 up"),
                     dict(node="cli", cmd="ip addr add 10.23.0.30/24 dev eth1 && ip link set eth1 up"),
                     dict(node="srv", cmd="mkdir -p /var/lib/ldap && chown openldap:openldap /var/lib/ldap"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m23-ldap",
        mgmt={"network": "clab-m23", "ipv4-subnet": "10.198.31.0/24"},
        topology=dict(
            nodes=dict(
                srv={"kind": "linux", "image": "netsys/labnode:3"},
                cli={"kind": "linux", "image": "netsys/labnode:3"},
            ),
            links=[["srv:eth1", "cli:eth1"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="slapd_listening", node="srv", cmd='ss -tln | grep -c "10.23.0.10:389"',
             expect="^[1-9]$", points=2,
             hint="slapd n'ecoute pas : ecrire /etc/ldap/slapd.conf (schemas core+cosine+inetorgperson, database mdb, suffix dc=lab23,dc=local, rootdn cn=admin,dc=lab23,dc=local, rootpw secret, directory /var/lib/ldap, modulepath /usr/lib/ldap + moduleload back_mdb) puis 'slapd -u openldap -g openldap -f /etc/ldap/slapd.conf -h ldap://10.23.0.10:389/' (etapes 1-2)."),
        dict(id="base_searchable", node="cli", cmd='ldapsearch -H ldap://10.23.0.10 -x -b dc=lab23,dc=local -s base dn 2>&1 | grep -c "dc=lab23"',
             expect="^[1-9]$", points=2,
             hint="La racine doit exister : importer /root/base.ldif (ldapadd -H ldap://10.23.0.10 -x -D cn=admin,dc=lab23,dc=local -w secret -f /root/base.ldif). L'entree dc=lab23,dc=local est le point d'entree de tout l'annuaire (etape 3)."),
        dict(id="user_elev1", node="cli", cmd='ldapsearch -H ldap://10.23.0.10 -x -b dc=lab23,dc=local "(uid=elev1)" uid 2>&1 | grep -c "uid: elev1"',
             expect="^[1-9]$", points=2,
             hint="L'utilisateur uid=elev1 doit etre present sous ou=People : verifier le ldif (objectClass inetOrgPerson) et 'ldapsearch -x -b dc=lab23,dc=local uid=elev1'."),
        dict(id="admin_bind", node="cli", cmd='ldapsearch -H ldap://10.23.0.10 -x -D cn=admin,dc=lab23,dc=local -w secret -b dc=lab23,dc=local dn 2>&1 | grep -c "result: 0 Success"',
             expect="^[1-9]$", points=2,
             hint="Le compte admin doit pouvoir se connecter (bind) avec le rootpw : un 'Invalid credentials' = rootpw different dans slapd.conf, 'Undefined attribute type' = schemas core/cosine/inetorgperson pas inclus."),
    ]),
    theory="""
# M23 — LDAP : l'annuaire des identités

## Pourquoi un annuaire central ?

Gérer `useradd` sur 200 machines = cauchemar. **LDAP** (Lightweight Directory
Access Protocol) centralise les identités dans un arbre :

```text
dc=lab23,dc=local            ← la base (suffix)
├── ou=People                ← unité d'organisation
│   └── uid=elev1            ← une entrée = un objet (attributs typés)
```

Chaque entrée a un **DN** (nom complet), des **objectClasses** (le contrat :
quels attributs sont obligatoires — ici `inetOrgPerson`) et des attributs.

## Le protocole, sans les mythes

- Port 389 (ldap://) ou 636 (ldaps://) — en lab, on écoute sur 389 en clair.
- Un client fait un **bind** (s'identifie : `-D cn=admin -w secret`) puis un
  **search** (filtre `(uid=elev1)`).
- Les ajouts passent par des fichiers **LDIF** importés avec `ldapadd`.

## slapd sans systemd

Le paquet `slapd` fournit le daemon. Sans systemd dans le conteneur, on le
conduit à la main : un `slapd.conf` minimal (backend `mdb`, suffix, rootdn,
rootpw, dossier de données), puis :

```text
slapd -u openldap -g openldap -f /etc/ldap/slapd.conf -h ldap://10.23.0.10:389/
```

## Étapes du lab

1. Écrire `/etc/ldap/slapd.conf` (les includes des schémas core + cosine + inetorgperson
   sont obligatoires pour `inetOrgPerson`).
2. Lancer slapd sur 10.23.0.10:389.
3. Importer la base (`dc=lab23,dc=local`, `ou=People`, `uid=elev1`) avec
   `ldapadd` en tant que rootdn.
4. Vérifier depuis `cli` : `ldapsearch -H ldap://10.23.0.10 -x -b dc=lab23,dc=local`.
""",
    quiz=dict(questions=[
        dict(q="Un DN dans LDAP, c'est :",
             choices=["Le mot de passe", "Le nom complet hiérarchique d'une entrée (uid=elev1,ou=People,dc=lab23,dc=local)", "Un fichier de log", "Un type d'index"],
             answer=1, points=1,
             expl="Le DN identifie un objet ; il se lit de la feuille vers la racine de l'arbre."),
        dict(q="Que définit une objectClass ?",
             choices=["La machine physique", "L'ensemble des attributs obligatoires/autorisés d'une entrée", "Le port d'écoute", "La replication"],
             answer=1, points=1,
             expl="La classe est un contrat : inetOrgPerson exige sn/cn, autorise uid, userPassword, mail..."),
        dict(q="Le 'suffix' dans slapd.conf :",
             choices=["Clôture les lignes LDIF", "Indique la racine de l'arbre que ce serveur sert", "Définit le mot de passe admin", "Filtre les recherches anonymes"],
             answer=1, points=1,
             expl="Un backend = une base ; le suffixe est sa racine (dc=lab23,dc=local)."),
        dict(q="Avant de créer uid=elev1 avec objectClass inetOrgPerson, il faut :",
             choices=["Rebooter le serveur", "Inclure les schémas core, cosine et inetorgperson dans slapd.conf", "Activer le TLS", "Créer le DNS"],
             answer=1, points=1,
             expl="Sans le schéma, l'attribut 'uid' est 'Undefined attribute type' — le piège classique."),
        dict(q="Le bind dans LDAP correspond à :",
             choices=["La sauvegarde", "L'authentification du client (DN + mot de passe)", "Le partitionnement", "La création du fichier de log"],
             answer=1, points=1,
             expl="On se présente avec -D (DN) et -w (mot de passe) ; 'Invalid credentials' = mauvais bind."),
        dict(q="Le format des fichiers d'import LDAP :",
             choices=["CSV", "JSON", "LDIF", "YAML"],
             answer=2, points=1,
             expl="LDIF = ligne 'dn:' puis 'attribut: valeur', entrées séparées par une ligne vide."),
    ]),
    scenario="""
# Scénario — L'école ouvre son annuaire

L'école (dc=lab23,dc=local) veut une seule liste d'identités : les élèves,
le personnel, et plus tard le Wi-Fi 802.1X. Vous posez le serveur pilote :
`srv` héberge l'annuaire LDAP, `cli` joue le poste d'admin.

1. Créer la config slapd (mdb, suffix dc=lab23,dc=local, rootdn cn=admin…).
2. Démarrer slapd sur 10.23.0.10:389.
3. Importer la base + un premier utilisateur (uid=elev1, mot de passe elev1pass).
4. Prouver depuis `cli` une recherche anonymes sur `(uid=elev1)` et un
   bind admin qui aboutit.

Question post-mortem : pourquoi l'annuaire refuse-t-il l'attribut `uid`
si les schémas ne sont pas chargés ?
""",
    solve={
        "srv": [f"echo {base64.b64encode(SLAPD_CONF.encode()).decode()} | base64 -d > /etc/ldap/slapd.conf", "slapd -u openldap -g openldap -f /etc/ldap/slapd.conf -h ldap://10.23.0.10:389/"],
        "cli": [f"echo {base64.b64encode(BASE_LDIF.encode()).decode()} | base64 -d > /root/base.ldif", "ldapadd -H ldap://10.23.0.10 -x -D cn=admin,dc=lab23,dc=local -w secret -f /root/base.ldif"],
    },
)

# ---------------------------------------------------------------- M24
DOVECOT_CONF = textwrap.dedent("""\
    dovecot_config_version = 2.4.0
    dovecot_storage_version = 2.4.0
    protocols = imap
    listen = 10.24.0.10
    ssl = no
    auth_allow_cleartext = yes
    auth_mechanisms = plain login
    mail_driver = mbox
    mail_inbox_path = /var/mail/%u
    mail_path = /var/mail/%u
    passdb pam {
      driver = pam
    }
    userdb passwd {
      driver = passwd
    }
""")

MODULES["M24-mail"] = dict(
    module=dict(
        id="M24",
        title="Mail : un serveur SMTP + IMAP fonctionnel",
        wave=4,
        prereqs=["M4", "M23"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=45,
                 setup=[
                     dict(node="mx", cmd="ip addr add 10.24.0.10/24 dev eth1 && ip link set eth1 up && hostname mx.lab24.local"),
                     dict(node="cli", cmd="ip addr add 10.24.0.30/24 dev eth1 && ip link set eth1 up"),
                     dict(node="mx", cmd="id alice >/dev/null 2>&1 || useradd -m alice; echo 'alice:secret' | chpasswd; mkdir -p /var/mail; touch /var/mail/alice; chown alice:mail /var/mail/alice; chmod 600 /var/mail/alice"),
                     dict(node="mx", cmd="echo 'Objectif : postfix (SMTP 25) + dovecot (IMAP 143) joignables depuis cli.' > /root/CONSIGNE.txt"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m24-mail",
        mgmt={"network": "clab-m24", "ipv4-subnet": "10.198.32.0/24"},
        topology=dict(
            nodes=dict(
                mx={"kind": "linux", "image": "netsys/labnode:3"},
                cli={"kind": "linux", "image": "netsys/labnode:3"},
            ),
            links=[["mx:eth1", "cli:eth1"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="smtp_listening", node="mx", cmd='ss -tln | grep -c ":25"',
             expect="^[1-9]$", points=2,
             hint="Postfix n'ecoute pas le 25 : 'postconf -e \\'myhostname = mx.lab24.local\\' ; postconf -e \\'mydestination = mx.lab24.local, localhost\\' ; postconf -e \\'inet_interfaces = all\\' ; postconf -e \\'mynetworks = 10.24.0.0/24\\' ; newaliases ; postfix start' (etape 1)."),
        dict(id="smtp_banner_cli", node="cli", cmd="timeout 3 bash -c 'exec 3<>/dev/tcp/10.24.0.10/25; head -1 <&3' | grep -c \"^220\"",
             expect="^1$", points=1,
             hint="Le banner 220 prouve que le service repond du LAN. Si connection refusee : inet_interfaces/myhostname (etape 1), verifier 'postfix status'."),
        dict(id="mail_delivered", node="mx", cmd='grep -c "sujet lab24" /var/mail/alice',
             expect="^[1-9]$", points=2,
             hint="Un message 'sujet lab24' doit atterrir dans la boite d'alice : envoyer 'echo sujet\\ lab24 | sendmail alice@mx.lab24.local' depuis cli ou mx. Si ca rebondit : mydestination ne couvre pas mx.lab24.local (etape 1), ou postfix pas demarre."),
        dict(id="imap_login", node="cli", cmd="curl -s -m 5 -u alice:secret imap://10.24.0.10/ | grep -c INBOX",
             expect="^[1-9]$", points=2,
             hint="Dovecot doit exposer IMAP sur 10.24.0.10:143 : ecrire /etc/dovecot/dovecot.conf aux normes 2.4 : en-tetes dovecot_config_version = 2.4.0 et dovecot_storage_version = 2.4.0, puis protocols = imap; listen = 10.24.0.10; ssl = no; auth_allow_cleartext = yes; auth_mechanisms = plain login; mail_driver = mbox; mail_inbox_path = /var/mail/%u; mail_path = /var/mail/%u; passdb pam { driver = pam }; userdb passwd { driver = passwd }. Lancer 'dovecot' (etape 2). 'doveconf -n' affiche l'erreur de config exacte."),
    ]),
    theory="""
# M24 — Mail : Postfix + Dovecot, le duo open source

## Le trajet d'un email

```text
expéditeur --SMTP:25--> serveur entrant (MX) --> boîte aux lettres
lecteur    --IMAP:143/993--> boîte aux lettres
```

- **SMTP** (Postfix) : protocole de *remise*. Le serveur « MX » accepte le
  message pour son domaine (`mydestination`).
- **IMAP** (Dovecot) : protocole de *lecture* — le client liste les dossiers
  et lit la boîte sans la déplacer.

## Postfix en 5 lignes de config

```text
myhostname     = mx.lab24.local
mydestination  = mx.lab24.local, localhost
inet_interfaces = all
mynetworks     = 10.24.0.0/24
```

`postconf -e` écrit ces paramètres, `newaliases` prépare les alias, puis
`postfix start` (pas de systemd ici). Une phrase résume la sécurité :
**jamais ouvert à tout le monde** (`mynetworks` strict) sinon votre serveur
devient un spammeur.

## Dovecot sans TLS, en lab

En prod : IMAPS 993 + certificats. Ici, `ssl = no` sur un LAN isolé
(Dovecot 2.4 accepte les mots de passe en clair sans TLS sur ce port). La boîte est un **mbox**
classique dans `/var/mail/<user>` ; l'auth passe par PAM (users système).

## Étapes du lab

1. `mx` : configurer et démarrer postfix ; `echo "sujet lab24" | sendmail alice@mx.lab24.local`.
2. `mx` : écrire /etc/dovecot/dovecot.conf et lancer `dovecot`.
3. `cli` : vérifier le banner `220`, puis `curl -u alice:secret imap://10.24.0.10/`
   → la boîte INBOX doit apparaître.
""",
    quiz=dict(questions=[
        dict(q="SMTP sert à :",
             choices=["Lire ses mails", "Transférer/remettre un message entre serveurs et vers la boîte", "Resolver le MX", "Chiffrer le sujet"],
             answer=1, points=1,
             expl="SMTP = remise ; la lecture côté client se fait par IMAP (ou POP3)."),
        dict(q="mydestination dans Postfix liste :",
             choices=["Les clients autorisés à envoyer", "Les domaines dont ce serveur est la destination finale", "Les MX de secours", "Les dossiers IMAP"],
             answer=1, points=1,
             expl="Un message pour un domaine hors mydestination sera refusé (relais non autorisé)."),
        dict(q="Un serveur postfix ouvert en relais (mynetworks = 0.0.0.0/0) :",
             choices=["Est plus rapide", "Accepte de re-router le spam du monde entier — blacklist immédiate", "Bloque les spams", "Chiffre pour les clients"],
             answer=1, points=1,
             expl="Le 'open relay' est la faute historique n°1 : on limite l'acceptation au réseau local ou authentifié."),
        dict(q="Dovecot, c'est le serveur :",
             choices=["SMTP sortant", "IMAP/POP — l'accès à la boîte pour les clients", "DNS des MX", "Filtre antispam uniquement"],
             answer=1, points=1,
             expl="Dovecot expose les boîtes via IMAP/POP3 et s'occupe de l'authentification des lecteurs."),
        dict(q="Le fichier /var/mail/alice en format mbox contient :",
             choices=["Les logs postfix", "Les messages de la boîte d'alice", "Les alias", "Les certificats"],
             answer=1, points=1,
             expl="mbox = un fichier, des messages concaténés avec des lignes 'From ' — dovecot le lit tel quel."),
        dict(q="Pourquoi le banner '220 mx...' vu par un client est utile au diagnostic ?",
             choices=["Il contient les mails", "Il prouve que TCP:25 est joignable et le service vivant", "Il signe le message", "Il configure le DNS"],
             answer=1, points=1,
             expl="Premier test de n'importe quel service réseau : la bannière initiale, avant toute commande du protocole."),
    ]),
    scenario="""
# Scénario — « On monte notre mail interne »

Le labo veut sa messagerie interne : pas de cloud, un serveur `mx` pour le
domaine `mx.lab24.local`, et alice (compte système déjà créé) comme seule
boîte. Vous livrez SMTP entrant + lecture IMAP.

1. Configurer Postfix (hostname, mydestination, inet_interfaces, mynetworks)
   et démarrer le service — `ss -tln` doit montrer le 25.
2. Envoyer un premier message « sujet lab24 » pour alice.
3. Écrire la config Dovecot (IMAP sur 10.24.0.10, mbox dans /var/mail, PAM)
   et la démarrer.
4. Depuis `cli` : banner 220 + `curl -u alice:secret imap://10.24.0.10/`
   qui renvoie la boîte INBOX.

Post-mortem : quel paramètre postfix aurait rendu la machine silencieusement
muette à vos messages ?
""",
    solve={
        "mx": [
            "postconf -e 'myhostname = mx.lab24.local' && postconf -e 'mydestination = mx.lab24.local, localhost' && postconf -e 'inet_interfaces = all' && postconf -e 'mynetworks = 10.24.0.0/24' && newaliases && postfix start",
            "echo 'sujet lab24' | sendmail alice@mx.lab24.local",
            f"echo {base64.b64encode(DOVECOT_CONF.encode()).decode()} | base64 -d > /etc/dovecot/dovecot.conf && dovecot",
        ],
    },
)

# ---------------------------------------------------------------- M25
PROM_YML = textwrap.dedent("""\
    global:
      scrape_interval: 5s
    scrape_configs:
      - job_name: tgt
        static_configs:
          - targets: ['10.25.0.20:9100']
""")
PROM_B64 = base64.b64encode(PROM_YML.encode()).decode()
PROM_FILE_CMD = f"echo {PROM_B64} | base64 -d > /root/prometheus.yml"

MODULES["M25-monitoring"] = dict(
    module=dict(
        id="M25",
        title="Monitoring : Prometheus qui surveille un hôte",
        wave=3,
        prereqs=["M3", "M10"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=30,
                 setup=[
                     dict(node="mon", cmd="ip addr add 10.25.0.10/24 dev eth1 && ip link set eth1 up && mkdir -p /var/lib/prometheus"),
                     dict(node="tgt", cmd="ip addr add 10.25.0.20/24 dev eth1 && ip link set eth1 up"),
                     dict(node="mon", cmd="echo 'Objectif: node_exporter sur tgt:9100, prometheus sur mon:9090, job nomme tgt.' > /root/CONSIGNE.txt"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m25-monitoring",
        mgmt={"network": "clab-m25", "ipv4-subnet": "10.198.33.0/24"},
        topology=dict(
            nodes=dict(
                mon={"kind": "linux", "image": "netsys/labnode:3"},
                tgt={"kind": "linux", "image": "netsys/labnode:3"},
            ),
            links=[["mon:eth1", "tgt:eth1"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="exporter_metrics", node="mon", cmd="curl -s -m 3 http://10.25.0.20:9100/metrics | grep -c '^node_cpu'",
             expect="^[1-9]", points=2,
             hint="Le node_exporter ne tourne pas (ou mal lie) sur tgt : 'node_exporter --web.listen-address=10.25.0.20:9100 &' sur tgt (le binaire est /usr/bin/prometheus-node-exporter : creer le lien node_exporter -> ce binaire) (etape 1)."),
        dict(id="prom_listening", node="mon", cmd='ss -tln | grep -c ":9090"',
             expect="^[1-9]$", points=1,
             hint="Prometheus doit ecouter 9090 : 'prometheus --config.file=/root/prometheus.yml --storage.tsdb.path=/var/lib/prometheus &' apres avoir ecrit la config (etape 2)."),
        dict(id="target_up", node="mon", cmd="""curl -s -m 5 http://localhost:9090/api/v1/targets | grep -c '"health":"up"'""",
             expect="^[1-9]$", points=2,
             hint="/root/prometheus.yml doit declarer un scrape_configs -> targets [10.25.0.20:9100]. 'health: up' = l'exporter est joint. Erreur de connexion : verifier l'IP du job ou le port (etape 1)."),
        dict(id="query_up_tgt", node="mon", cmd="""curl -s -m 5 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22tgt%22%7D' | grep -c '"1"'""",
             expect="^[1-9]$", points=2,
             hint="La requete 'up{job=\"tgt\"}' doit renvoyer 1 : le job s'appelle exactement 'tgt' dans la config (job_name: tgt) et a ete scrape au moins une fois (etape 2-3)."),
    ]),
    theory="""
# M25 — Monitoring avec Prometheus

## Le pull, pas le push

Prometheus **sonde** (*scrape*) chaque cible HTTP qui expose `/metrics` :
`node_exporter` publie CPU, mémoire, disques, réseau, au format texte
`node_cpu_seconds_total{cpu="0",mode="idle"} 123.45`. La cible n'envoie rien :
le collecteur passe la prendre. C'est le modèle « pull », plus tolérant aux
pannes des cibles.

## Les trois blocs d'une config

```yaml
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: tgt
    static_configs:
      - targets: ['10.25.0.20:9100']
```

- **job** : le nom qui apparaîtra dans les métriques (`up{job="tgt"}`).
- **up** : métrique interne = 1 si le scrape vient, 0 sinon. Le premier réflexe
  d'un admin : « mes cibles sont-elles up ? ».
- **PromQL** : le langage de requête (`up{job="tgt"}`, `rate(...)`…).

## Sans systemd

Les deux binaires se lancent à la main (en tâche de fond `&`) ; en prod
systemd ou k8s s'en charge. On garde la même philosophie : un process
exporter par machine, un serveur prometheus, et l'API HTTP pour tout vérifier.

## Étapes du lab

1. `tgt` : lancer `node_exporter` (listen 10.25.0.20:9100).
2. `mon` : écrire `/root/prometheus.yml` (job `tgt` vers `10.25.0.20:9100`) et
   lancer `prometheus`.
3. `mon` : vérifier `/api/v1/targets` (health up) puis la requête
   `up{job="tgt"}` dans `/api/v1/query`.
""",
    quiz=dict(questions=[
        dict(q="Prometheus récupère les métriques en :",
             choices=["Push depuis les hôtes", "Scraping HTTP périodique vers /metrics", "Syslog", "SNMP uniquement"],
             answer=1, points=1,
             expl="Modèle pull : le serveur sonde les cibles ; une cible en panne ne gêne que son propre état."),
        dict(q="Que mesure la métrique 'up' ?",
             choices=["L'uptime", "Si le dernier scrape de la cible a réussi (1) ou non (0)", "La charge CPU", "Les baux DHCP"],
             answer=1, points=1,
             expl="up{job=...} est le signal vital n°1 : 0 = cible injoignable, exporter HS ou erreur de config."),
        dict(q="node_exporter expose ses métriques sur :",
             choices=["Un fichier syslog", "HTTP /metrics (port 9100 par défaut)", "UDP 161", "SMTP"],
             answer=1, points=1,
             expl="C'est un mini serveur HTTP qui sérialise les compteurs du système."),
        dict(q="job_name dans prometheus.yml :",
             choices=["Identifie le job de scrape et étiquette les métriques (job=...)", "Choisit le port", "Fixe le TTL", "Active l'alerte"],
             answer=0, points=1,
             expl="C'est le libellé 'job' ; d'où la requête up{job='tgt'}."),
        dict(q="Le scrape_interval global sert à :",
             choices=["Nettoyer le stockage", "Fixer la fréquence de passage sur chaque cible", "Authentifier l'exporter", "Limiter les requêtes Grafana"],
             answer=1, points=1,
             expl="Par défaut 1 min — en lab on le baisse (5 s) pour voir 'up' arriver vite."),
        dict(q="Pourquoi un pull modèle aide-t-il en cas de panne réseau ?",
             choices=["Les hôtes envoient en rafale", "Une cible injoignable produit simplement up=0 sans bloquer le serveur", "Les métriques sont locales", "Le DNS n'est pas requis"],
             answer=1, points=1,
             expl="Le serveur ne dépend que de ses scrapeurs ; pas de flood ni de files d'attente côté clients."),
    ]),
    scenario="""
# Scénario — Le serveur de supervision du labo

Le chef d'atelier veut voir « d'un coup d'œil » si les machines vivent.
Vous installez le standard de fait : un hôte cible `tgt` avec son
**node_exporter**, et une machine `mon` qui héberge **Prometheus**.

1. Démarrer l'exporter sur `tgt` (port 9100, interface LAN).
2. Configurer le job `tgt` sur `mon` et démarrer prometheus (9090).
3. Prouver via l'API : cible 'health: up' et requête `up{job="tgt"} == 1`.
4. Question post-mortem : si `up` tombe à 0, quels trois réflexes ?
   (la cible répond-elle en HTTP ? le port ? le job pointe-t-il la bonne IP ?)
""",
    solve={
        "tgt": ["ln -sf /usr/bin/prometheus-node-exporter /usr/local/bin/node_exporter 2>/dev/null; node_exporter --web.listen-address=10.25.0.20:9100 >/root/node_exporter.log 2>&1 &"],
        "mon": [PROM_FILE_CMD, "prometheus --config.file=/root/prometheus.yml --storage.tsdb.path=/var/lib/prometheus >/root/prometheus.log 2>&1 &"],
    },
)

# ---------------------------------------------------------------- M26
DHCPSMASQ = textwrap.dedent("""\
    port=0
    interface=eth1
    dhcp-range=10.26.2.100,10.26.2.150,255.255.255.0,8h
    dhcp-option=3,10.26.2.1
    log-dhcp
""")

MODULES["M26-dhcp-relay"] = dict(
    module=dict(
        id="M26",
        title="DHCP à travers les routes : le relais",
        wave=4,
        prereqs=["M4", "M6"],
        status="full",
        lab=dict(mode="topology", dir="lab", topo="topology.yaml", checks="checks.yaml", ttl_min=45,
                 setup=[
                     dict(node="srv", cmd="ip addr add 10.26.1.10/24 dev eth1 && ip link set eth1 up && ip route replace 10.26.2.0/24 via 10.26.1.1 dev eth1 && sysctl -qw net.ipv4.ip_forward=1"),
                     dict(node="rtr", cmd="ip addr add 10.26.1.1/24 dev eth2 && ip addr add 10.26.2.1/24 dev eth1 && ip link set eth1 up && ip link set eth2 up && sysctl -qw net.ipv4.ip_forward=1"),
                     dict(node="cli", cmd="ip link set eth1 up"),
                     file_cmd("srv", "/root/dnsmasq.conf", DHCPSMASQ),
                     dict(node="srv", cmd="echo 'Le DHCP est cote srv (10.26.1.0/24) ; les clients sont sur LAN2 (10.26.2.0/24) sans serveur. srv a deja une route de retour vers 10.26.2.0/24 via rtr (sinon la reponse part dans le vide).' > /root/CONSIGNE.txt"),
                 ]),
        validation=dict(quiz_min_score=70, lab_required=True),
    ),
    topo=dict(
        name="m26-dhcp-relay",
        mgmt={"network": "clab-m26", "ipv4-subnet": "10.198.34.0/24"},
        topology=dict(
            nodes=dict(
                srv={"kind": "linux", "image": "netsys/labnode:3"},
                rtr={"kind": "linux", "image": "netsys/labnode:3"},
                cli={"kind": "linux", "image": "netsys/labnode:3"},
            ),
            links=[["cli:eth1", "rtr:eth1"], ["rtr:eth2", "srv:eth1"]],
        ),
    ),
    checks=dict(checks=[
        dict(id="dhcp_srv_up", node="srv", cmd='ss -uln | grep -c ":67"',
             expect="^[1-9]$", points=1,
             hint="Le serveur DHCP ne tourne pas sur srv : 'dnsmasq --conf-file=/root/dnsmasq.conf' (le fichier existe, port=0 = DHCP seul). Verifier 'ss -uln | grep :67' (etape 1)."),
        dict(id="relay_running", node="rtr", cmd="pgrep -x dhcrelay",
             points=2,
             hint="Le routeur ne relais pas : 'dhcrelay 10.26.1.10' — il ecoute sur toutes les interfaces (dont eth1 cote clients) et forward vers le serveur 10.26.1.10 (etape 2)."),
        dict(id="lease_obtained", node="cli", cmd='ip -4 addr show dev eth1 | grep -Ec "inet 10\\.26\\.2\\.1[0-4][0-9]/24"',
             expect="^[1-9]$", points=2,
             hint="La machine cliente n'a pas de bail dans le pool : lancer 'dhclient eth1' sur cli. Sans relais actif (check precedent) le DISCOVER reste confine au LAN (etape 3)."),
        dict(id="gw_option", node="cli", cmd="grep -c 'routers 10[.]26[.]2[.]1' /var/lib/dhcp/dhclient.leases",
             expect="^[1-9]$", points=2,
             hint="L'option 3 (routers) du bail doit etre 10.26.2.1 : lire 'grep routers /var/lib/dhcp/dhclient.leases' (le dernier bail est en haut). Si rien : 'dhclient eth1' n'a pas abouti ou l'option 3 manque dans /root/dnsmasq.conf (etape 1-3)."),
        dict(id="ping_gw_from_cli", node="cli", cmd="ping -c2 -W2 10.26.2.1", expect="0% packet loss", points=3,
             hint="Test final : le client doit joindre sa passerelle 10.26.2.1 (l'autre face du routeur qui a fait le relais). Si ca echoue : 'ip route get 10.26.2.1' et bail correct sur eth1 (etape 3)."),
    ]),
    theory="""
# M26 — DHCP à travers les routes

## Le problème : le DHCP est « local de lien »

Le client envoie un **DHCPDISCOVER** en broadcast 255.255.255.255 (ou
255.255.255.255:68 depuis 0.0.0.0) **avant d'avoir une IP**. Un routeur ne
relaie pas les broadcasts : le serveur DHCP du réseau d'à côté ne l'entend
jamais. Sans solution, il faudrait un DHCP par sous-réseau.

## Le relais DHCP (RFC 2131)

Un routeur-configuré-en-relais :

1. reçoit le DISCOVER diffusé sur l'interface du client,
2. le convertit en **unicast** vers le serveur,
3. écrit dans le champ **giaddr** « l'IP de l'interface où le client se trouve »,
4. le serveur, grâce à giaddr, **choisit le pool du client** (10.26.2.0/24 ici),
5. la réponse revient via le relais qui la diffuse au client.

Attention : dnsmasq **unicaste sa réponse vers giaddr** (10.26.2.1 ici). Si
`srv` n'a pas de route vers le réseau des clients, l'OFFER est calculée,
loguée… et jamais envoyée. D'où la route de retour
`ip route replace 10.26.2.0/24 via 10.26.1.1` donnée dans le setup.

Chez Debian : le binaire `dhcrelay` (paquet isc-dhcp-relay). Un seul mot
compte : `dhcrelay <ip-du-serveur>` — il écoute sur toutes les interfaces.

## Le client

`dhclient eth1` fait le DORA complet : Discover, Offer, Request, Ack.
Après quoi l'interface porte l'IP du pool et la **route par défaut option 3**.

## Étapes du lab

1. `srv` : démarrer `dnsmasq --conf-file=/root/dnsmasq.conf` (pool 10.26.2.100-150).
2. `rtr` : `dhcrelay 10.26.1.10`.
3. `cli` : `dhclient eth1` → bail dans le pool, default gw 10.26.2.1.
4. Prouver la continuité : `ping 10.26.2.1` depuis `cli` — la passerelle
   reçue dans le bail répond, le routeur est bien vivant des deux côtés.
   (Note : le réseau de management du labo est *aussi* en DHCP, donc la
   default route installée par `dhclient eth1` peut rester celle d'eth0 ;
   l'option 3 du bail se lit dans `/var/lib/dhcp/dhclient.leases`.)
""",
    quiz=dict(questions=[
        dict(q="Pourquoi un client DHCP sans IP ne peut-il pas joindre un serveur sur un autre sous-réseau ?",
             choices=["Le DNS est mort", "Il diffuse en broadcast, qu'un routeur ne relaie pas", "Le MTU est nul", "Il attend le DHCP INFORM"],
             answer=1, points=1,
             expl="Avant d'avoir une adresse, le client ne peut que parler en broadcast local — d'où le relais."),
        dict(q="Le champ giaddr dans la requête DHCP relayée contient :",
             choices=["La MAC du client", "L'IP de l'interface du relais côté client", "Le serveur", "Le bail"],
             answer=1, points=1,
             expl="giaddr identifie le sous-réseau d'origine : le serveur choisit le pool correspondant."),
        dict(q="Sans relais, la solution naïve (et coûteuse) est :",
             choices=["Un DHCP par sous-réseau", "NAT", "DNS dynamique", "Baux statiques"],
             answer=0, points=1,
             expl="On duplique le serveur sur chaque LAN — le relais centralise précisément pour l'éviter."),
        dict(q="DORA signifie :",
             choices=["Discover, Offer, Request, Ack", "Domain, Origin, Relay, Address", "Default, Option, Route, ARP", "DHCP Over RDMA"],
             answer=0, points=1,
             expl="Le dialogue complet d'un bail DHCP."),
        dict(q="L'option DHCP 3 porte :",
             choices=["Le nom de domaine", "La passerelle par défaut", "Le serveur NTP", "Le bail"],
             answer=1, points=1,
             expl="Option 3 = router : la default route que dhclient installe."),
        dict(q="Le port UDP du serveur DHCP (messages clients) est :",
             choices=["67", "68", "53", "520"],
             answer=0, points=1,
             expl="67 côté serveur, 68 côté client — ss -uln | grep :67 est votre preuve de service vivant."),
    ]),
    scenario="""
# Scénario — Le deuxième étage n'a pas de serveur DHCP

Le réseau du labo s'agrandit : LAN1 `10.26.1.0/24` (où vit le serveur DHCP
`srv`), LAN2 `10.26.2.0/24` au deuxième étage, séparé par le routeur `rtr`.
Le pool pour LAN2 est déjà écrit dans /root/dnsmasq.conf, la passerelle
`10.26.2.1` est configurée sur `rtr`. Les machines du deuxième étage
n'obtiennent RIEN — pas d'IP, pas de passerelle, pas de sortie.

1. Démarrer le serveur DHCP sur `srv`.
2. Transformer `rtr` en relais DHCP vers 10.26.1.10.
3. Sur `cli` (LAN2) : obtenir un bail (`dhclient eth1`), vérifier IP dans
   10.26.2.100-150 et l'option `routers 10.26.2.1` dans
   `/var/lib/dhcp/dhclient.leases`.
4. Continuité : `ping 10.26.2.1` depuis le client.

Question post-mortem : quel champ de la trame a permis au serveur de choisir
le bon pool, sans connaître la topologie ?
""",
    solve={
        "srv": ["dnsmasq --conf-file=/root/dnsmasq.conf"],
        "rtr": ["dhcrelay 10.26.1.10"],
        "cli": ["dhclient eth1"],
    },
)


for name, m in MODULES.items():
    d = mod_dir(name)
    m["topo"]["topology"]["links"] = [{"endpoints": l} for l in m["topo"]["topology"]["links"]]
    dump(d / "module.yaml", m["module"])
    dump(d / "lab" / "topology.yaml", m["topo"])
    dump(d / "lab" / "checks.yaml", m["checks"])
    dump(d / "quiz.yaml", m["quiz"])
    write(d / "theory.md", m["theory"])
    write(d / "lab" / "scenario.md", m["scenario"])
    Path(ROOT).parent.joinpath("tests", f"solve_{m['module']['id']}.json").write_text(json.dumps(m["solve"], indent=1))
    print("écrit", name)
print("OK", len(MODULES), "modules")
