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
