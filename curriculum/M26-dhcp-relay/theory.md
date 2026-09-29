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
