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
