# Labo M11 — Pare-feu à zones et NAT avec nftables

**Objectif** : transformer `fw` en pare-feu à deux zones. Le LAN (10.10.110.0/24) sort
vers la WAN (10.10.120.0/24) grâce au **NAT masquerade**, la WAN **ne peut pas** joindre
le LAN en ICMP, et un service du LAN est publié vers l'extérieur par une règle de
**DNAT** (port 8080 → `lan:80`). La politique s'appuie sur le suivi d'état (conntrack).

Cliquez sur un nœud de la topologie pour ouvrir son **terminal** ; l'**Éditeur de
configuration** écrit directement un fichier dans le nœud choisi — utilisez-le pour
`/root/nft.rules` (le jeu de règles) puis `/root/nft.conf.set` (l'archivage). Cliquez sur
**Vérifier** pour les 7 checks (10 points).

## Plan d'adressage

| Nœud | Interface | Adresse | Rôle |
|---|---|---|---|
| lan | eth1 | 10.10.110.10/24 | serveur web (zone LAN) |
| fw | eth1 / eth2 | 10.10.110.1/24 / 10.10.120.1/24 | pare-feu, 2 zones |
| wan | eth1 | 10.10.120.20/24 | client « Internet » |

**Volontairement, `wan` n'aura aucune route vers 10.10.110.0/24** : c'est le NAT qui doit
rendre la réponse possible.

## Étape 1 — Adressage et transit

```bash
# lan :
ip link set eth1 up && ip addr add 10.10.110.10/24 dev eth1
ip route replace default via 10.10.110.1      # replace : écrase la route de management
# fw :
ip link set eth1 up; ip link set eth2 up
ip addr add 10.10.110.1/24 dev eth1; ip addr add 10.10.120.1/24 dev eth2
sysctl -w net.ipv4.ip_forward=1
# wan :
ip link set eth1 up && ip addr add 10.10.120.20/24 dev eth1
```

Test sans pare-feu : depuis `lan`, `ping -c2 10.10.120.20` échoue (100 % de perte) alors
que les requêtes partent — `wan` ne sait pas revenir vers 10.10.110.10. Observez depuis
`fw` : `tcpdump -ni eth2 -c 4 icmp`. C'est exactement ce que le NAT masquerade va résoudre.

## Étape 2 — NAT masquerade (sortie LAN → WAN)

```bash
nft add table ip nat
nft add chain ip nat postrouting '{ type nat hook postrouting priority srcnat ; policy accept ; }'
nft add rule ip nat postrouting ip saddr 10.10.110.0/24 oifname eth2 masquerade
```

`masquerade` = `snat to <adresse de l'interface sortante>` : utile quand cette adresse
n'est pas fixe. Le ping `lan → wan` doit passer à 0 % de perte ; vérifiez la translation
dans la table de connexion : `cat /proc/net/nf_conntrack | grep 10.10.110.10`.

## Étape 3 — Publier un service du LAN (DNAT)

```bash
# sur lan :
nohup python3 -m http.server 80 > /dev/null 2>&1 &
# sur fw :
nft add chain ip nat prerouting '{ type nat hook prerouting priority dstnat ; policy accept ; }'
nft add rule ip nat prerouting iifname eth2 meta l4proto tcp tcp dport 8080 dnat to 10.10.110.10:80
```

Depuis `wan` : `curl -i http://10.10.120.1:8080` doit renvoyer un `200 OK`. La règle ne
fait que réécrire la destination ; le retour est dé-traduit automatiquement par conntrack.

## Étape 4 — Politique stateful par zones (à écrire dans /root/nft.rules)

Éditeur, nœud `fw`, chemin `/root/nft.rules` :

```
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0 ; policy drop ;
        ct state established,related accept
        iifname lo accept
        iifname eth0 accept                          # management containerlab
        iifname eth1 accept                          # le LAN est de confiance
        iifname eth2 icmp type echo-request accept   # le pare-feu répond aux pings entrants
        iifname eth2 drop                            # le reste de la WAN est coupé
    }
    chain forward {
        type filter hook forward priority 0 ; policy drop ;
        ct state established,related accept          # les retours passent toujours
        iifname eth1 accept                          # LAN -> WAN autorisé
        iifname eth2 ip protocol icmp drop           # pas d'ICMP entrant vers le LAN
        iifname eth2 meta l4proto tcp tcp dport 80 accept   # trafic DNATé vers lan:80
    }
    chain output {
        type filter hook output priority 0 ; policy accept ;
    }
}

table ip nat {
    chain prerouting {
        type nat hook prerouting priority dstnat ; policy accept ;
        iifname eth2 meta l4proto tcp tcp dport 8080 dnat to 10.10.110.10:80
    }
    chain postrouting {
        type nat hook postrouting priority srcnat ; policy accept ;
        ip saddr 10.10.110.0/24 oifname eth2 masquerade
    }
}
```

Puis :

```bash
nft -f /root/nft.rules
nft list ruleset
```

La règle `ct state established,related accept` **doit** précéder le drop d'ICMP : sinon
les réponses aux pings partants du LAN seraient jetées à leur tour (elles entrent bien
par `eth2`). C'est tout l'intérêt d'un pare-feu à états : on autorise un flux en évaluant
sa direction, pas seulement son adresse.

## Étape 5 — Tests croisés

```bash
lan#  ping -c2 10.10.120.20            # OK 0 % de perte (transit + NAT)
wan#  ping -c2 10.10.110.10            # ÉCHEC (ICMP entrant bloqué)
wan#  ping -c2 10.10.120.1             # OK : le pare-feu répond, limite 5/s
wan#  curl -i -m 5 http://10.10.120.1:8080   # OK 200 (DNAT)
fw#   grep 10.10.110 /proc/net/nf_conntrack   # entrées de la table de connexion (NAT visible)
```

Pour débiter une règle qui ne laisse pas passer le trafic attendu :
`nft add rule inet filter forward ip daddr 10.10.110.10 meta nftrace set 1` puis
`nft monitor trace` affiche la chaîne de décision paquet par paquet.

## Étape 6 — Archiver la configuration

```bash
nft list ruleset > /root/nft.conf.set
grep -c masquerade /root/nft.conf.set
```

`nft list ruleset` est l'équivalent du `show running-config` d'un équipement : c'est le
seul artefact à versionner (le fichier source `/root/nft.rules` est à garder aussi, lui
seul est relisible et rechargeable par `nft -f`).

Cliquez **Vérifier** : transit + NAT, blocage ICMP entrant, DNAT 8080 → lan:80, règles
présentes dans le jeu actif et jeu archivé dans `/root/nft.conf.set`.
