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
